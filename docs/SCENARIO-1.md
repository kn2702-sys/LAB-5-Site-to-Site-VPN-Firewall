# Scenario 1: Tunnel established, no traffic

**File:** `Lab-5-SCENARIO-1-Tunnel-Up-No-Traffic.pkt`

**Symptom.** PC-A1 (`10.10.10.10`) cannot ping PC-B1 (`10.20.20.10`).
The tunnel *looks* fine.

**The rule for this scenario:** when SAs exist, the control plane is
innocent. Investigate the data plane — in this order:

```
tunnel state → selectors → NAT exemption → routes → firewall policy
```

---

## 1. Tunnel state — is the control plane actually healthy?

**Where:** FW-A (and FW-B).

```
show crypto isakmp sa
```

**Expect:** a line ending in `QM_IDLE` — Phase 1 is up.

```
show crypto ipsec sa
```

**Expect:** an inbound and outbound SA, with `pkts encaps` growing on FW-A
as you ping.

**Result here:** ✅ Both show healthy SAs. Do **not** rebuild the tunnel,
do not touch the PSK, do not "fix" Phase 1. The most common mistake in
this scenario is re-doing crypto config that was never broken.

## 2. Selectors — do both ends agree on *what* is encrypted?

**Where:** `show crypto ipsec sa` output, both routers.

Look for the proxy identities:

```
local ident (addr/mask/prot/port): (10.10.10.0/255.255.255.0/0/0)
remote ident (addr/mask/prot/port): (10.20.20.0/255.255.255.0/0/0)
```

**Result here:** ✅ mirror images on both ends. A mismatch here (e.g. one
side's ACL 100 uses a wrong wildcard) kills Phase 2 — but then the tunnel
wouldn't be up, so this check is really about building the habit.

## 3. NAT exemption — is VPN traffic escaping translation?

**Where:** FW-A.

```
show ip nat translations
```

**Expect:** while pinging across the tunnel, you see **no** translation
entries with source `10.10.10.10` → the VPN traffic must skip NAT (ACL 101
`deny`s it first).

**Result here:** ✅ no translations for VPN traffic — exemption is working.
If you *did* see `10.10.10.10` translated to `203.0.113.1`, the crypto
selectors would stop matching and the tunnel would flap or go idle. NAT
exemption is always worth checking because it's invisible until it breaks.

## 4. Routes — can each end reach the other's *encrypted* destination?

**Where:** FW-A, FW-B.

```
show ip route
```

**Expect:** default route toward the ISP on both; the crypto map handles
stealing interesting traffic, so no special tunnel route is needed in this
design.

**Result here:** ✅ routing is fine.

## 5. Firewall policy — what happens *after* decryption?

This is where the trail ends. On FW-B:

```
show access-lists 150
```

**Result here:** ❌ the `deny ip 10.10.10.0 0.0.0.255 10.20.20.0 0.0.0.255`
line has climbing match counters. Someone applied an outbound ACL on FW-B's
inside interface (`ip access-group 150 out` on `GigabitEthernet0/0/0`) that
drops the VPN traffic **after** it is decrypted.

Notice the evidence chain that convicted the firewall, not the VPN:
- `show crypto ipsec sa` on FW-B: `pkts decaps` **grows** — packets arrive
  and decrypt successfully.
- `show access-lists 150`: deny matches grow in lockstep with your pings.
- The tunnel never flapped. The control plane was never the problem.

## The fix

On **FW-B**:

```
configure terminal
interface GigabitEthernet0/0/0
 no ip access-group 150 out
end
```

(Or correct ACL 150's first line if the intent was to filter something
else.) Then verify from PC-A1:

```
ping 10.20.20.10        ✅
```

And on FW-B, `show crypto ipsec sa` — encaps *and* decaps now grow on both
ends.

## The takeaway

"VPN is down" splits into two completely different investigations. This
scenario trains the reflex: **SAs up → stop touching crypto → walk the data
plane.** In a NOC, that reflex is the difference between a 5-minute fix and
an hour of rebuilding a healthy tunnel.
