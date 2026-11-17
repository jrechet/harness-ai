package main

import "testing"

func TestCheck(t *testing.T) {
	cases := []struct {
		name string
		diff string
		want int
	}{
		{"no change", "", 0},
		{"new migration", "A\tmigrations/0004_fees.sql\n", 0},
		{"edited migration", "M\tmigrations/0002_transfers.sql\n", 1},
		{"deleted migration", "D\tmigrations/0001_accounts.sql\n", 1},
		{"renamed migration", "R100\tmigrations/0003_a.sql\tmigrations/0003_b.sql\n", 1},
		{"mixed", "A\tmigrations/0004_x.sql\nM\tmigrations/0001_accounts.sql\n", 1},
	}
	for _, c := range cases {
		if got := Check(c.diff); len(got) != c.want {
			t.Errorf("%s: got %d violation(s) %v, want %d", c.name, len(got), got, c.want)
		}
	}
}
