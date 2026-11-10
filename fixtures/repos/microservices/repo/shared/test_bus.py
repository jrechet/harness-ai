import unittest

from shared.bus import InMemoryBus, envelope


def ping(event_id="ping:1"):
    return envelope("ping", event_id, "2026-06-02T12:00:00+00:00", {"n": 1})


class InMemoryBusTest(unittest.TestCase):
    def test_every_event_is_delivered_twice_by_default(self):
        bus, seen = InMemoryBus(), []
        bus.subscribe("ping", lambda event: seen.append(event["id"]))
        bus.publish(ping())
        self.assertEqual(seen, ["ping:1", "ping:1"])

    def test_the_second_delivery_comes_after_every_subscriber_got_the_first(self):
        bus, seen = InMemoryBus(), []
        bus.subscribe("ping", lambda event: seen.append("a"))
        bus.subscribe("ping", lambda event: seen.append("b"))
        bus.publish(ping())
        self.assertEqual(seen, ["a", "b", "a", "b"])

    def test_one_delivery_can_be_asked_for(self):
        bus, seen = InMemoryBus(deliveries=1), []
        bus.subscribe("ping", lambda event: seen.append(event["id"]))
        bus.publish(ping())
        self.assertEqual(seen, ["ping:1"])

    def test_zero_deliveries_is_refused(self):
        with self.assertRaises(ValueError):
            InMemoryBus(deliveries=0)

    def test_a_subscriber_only_gets_its_event_type(self):
        bus, seen = InMemoryBus(), []
        bus.subscribe("pong", seen.append)
        bus.publish(ping())
        self.assertEqual(seen, [])

    def test_each_delivery_is_a_copy(self):
        bus, seen = InMemoryBus(), []

        def greedy(event):
            seen.append(event["payload"]["n"])
            event["payload"]["n"] += 1

        bus.subscribe("ping", greedy)
        bus.publish(ping())
        self.assertEqual(seen, [1, 1])

    def test_published_lists_each_event_once(self):
        bus = InMemoryBus()
        bus.publish(ping("ping:1"))
        bus.publish(envelope("pong", "pong:1", "2026-06-02T12:00:00+00:00", {}))
        self.assertEqual([e["id"] for e in bus.published()], ["ping:1", "pong:1"])
        self.assertEqual([e["id"] for e in bus.published("pong")], ["pong:1"])


if __name__ == "__main__":
    unittest.main()
