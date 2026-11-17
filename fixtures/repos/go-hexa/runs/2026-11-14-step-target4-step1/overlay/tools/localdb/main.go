// Command localdb fails unless DATABASE_URL designates the developer's own
// local PostgreSQL. `make migrate` and `make reset-db` call it before psql:
// reset-db drops the whole schema without looking at the target, and on
// 2026-02-03 it ran against staging and destroyed two days of QA data
// (docs/operations.md). Staging and production are only migrated by
// deploy.yml, which calls psql directly, so there is no override.
//
//	go run ./tools/localdb   # exit 0, or 1 with the offending host
//
// Local means: localhost, 127.0.0.1 (any 127.x), ::1, or a Unix socket
// (empty host, or a host starting with "/"). An empty host falls back to
// PGHOST / PGHOSTADDR, as psql does.
package main

import (
	"fmt"
	"net"
	"net/url"
	"os"
	"strings"
)

// Check returns nil when every host targeted by dsn is local. getenv supplies
// PGHOST and PGHOSTADDR, which psql uses when the DSN names no host.
func Check(dsn string, getenv func(string) string) error {
	dsn = strings.TrimSpace(dsn)
	if dsn == "" {
		return fmt.Errorf("DATABASE_URL is empty")
	}
	hosts, err := targets(dsn)
	if err != nil {
		return err
	}
	if len(hosts) == 0 {
		for _, k := range []string{"PGHOSTADDR", "PGHOST"} {
			if v := getenv(k); v != "" {
				hosts = splitHosts(v)
				break
			}
		}
	}
	for _, h := range hosts {
		if !isLocal(h) {
			return fmt.Errorf("host %q is not local", h)
		}
	}
	return nil
}

// targets lists the hosts named by a URL or a keyword/value connection string.
func targets(dsn string) ([]string, error) {
	if strings.HasPrefix(dsn, "postgres://") || strings.HasPrefix(dsn, "postgresql://") {
		u, err := url.Parse(dsn)
		if err != nil {
			return nil, fmt.Errorf("cannot parse DATABASE_URL: %v", err)
		}
		q := u.Query()
		// Query parameters take precedence over the authority, as in libpq.
		for _, k := range []string{"hostaddr", "host"} {
			if v := q.Get(k); v != "" {
				return splitHosts(v), nil
			}
		}
		return splitHosts(u.Host), nil
	}
	if strings.Contains(dsn, "=") {
		var hosts []string
		for _, f := range strings.Fields(dsn) {
			k, v, ok := strings.Cut(f, "=")
			if ok && (k == "host" || k == "hostaddr") {
				hosts = append(hosts, splitHosts(strings.Trim(v, "'"))...)
			}
		}
		return hosts, nil
	}
	return nil, fmt.Errorf("DATABASE_URL is neither a postgres:// URL nor a key=value string")
}

func splitHosts(s string) []string {
	var hosts []string
	for _, h := range strings.Split(s, ",") {
		h = strings.TrimSpace(h)
		if h == "" {
			continue
		}
		if hh, _, err := net.SplitHostPort(h); err == nil {
			h = hh
		}
		hosts = append(hosts, strings.Trim(h, "[]"))
	}
	return hosts
}

func isLocal(h string) bool {
	if strings.HasPrefix(h, "/") || strings.EqualFold(h, "localhost") {
		return true
	}
	ip := net.ParseIP(h)
	return ip != nil && ip.IsLoopback()
}

func main() {
	if err := Check(os.Getenv("DATABASE_URL"), os.Getenv); err != nil {
		fmt.Fprintf(os.Stderr, "localdb: %v; make migrate and make reset-db only run on your own local database (docs/operations.md)\n", err)
		os.Exit(1)
	}
}
