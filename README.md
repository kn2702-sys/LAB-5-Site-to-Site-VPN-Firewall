# Lab 5: Site-to-Site VPN + Firewall

Two offices joined by an **IPsec site-to-site VPN** across a simulated
internet, each guarded by firewall policy — built as a *conceptual* lab in
Cisco Packet Tracer. Includes two broken variants, one per classic failure
mode, so you practice diagnosing VPNs the way a NOC does.

> **What this is:** hands-on IPsec fundamentals — IKE Phase 1/2, interesting
> traffic (selectors), NAT exemption, tunnel establishment, firewall policy
> behavior. The concepts map directly to Palo Alto, Fortinet and Juniper;
> see [docs/VPN-CONCEPTS.md](docs/VPN-CONCEPTS.md).
>
> **Résumé line:** *Built and troubleshot a site-to-site VPN lab covering
> routing, tunnel establishment and firewall policy behavior.*
>
> **Don't claim:** *"I deployed enterprise IPsec VPN."*

## Skills demonstrated

- Site-to-site IPsec VPN: IKE policy, pre-shared-key auth, transform sets,
  crypto maps, PFS
- Interesting traffic / selectors: only defined traffic enters the tunnel
- NAT exemption: keeping VPN traffic untranslated (the silent killer)
- Firewall policy with extended ACLs, ordered allow/deny
- Two failure modes, two investigations: tunnel-up-no-traffic (data plane)
  vs tunnel-down (control plane)

## Topology

```
Office A  10.10.10.0/24                    Office B  10.20.20.0/24
  .10      .11                                .10      .11
 PC-A1    PC-A2                              PC-B1    PC-B2
   | Fa0/1  | Fa0/2                           | Fa0/1  | Fa0/2
   +--------+                                 +--------+
        | Fa0/24                                   | Fa0/24
      [SW-A]                                     [SW-B]
        | G0/0/0  10.10.10.1                       | G0/0/0  10.20.20.1
       [FW-A]  ← IPsec + firewall                [FW-B]  ← IPsec + firewall
        | G0/0/1  203.0.113.1                      | G0/0/1  198.51.100.2
        |  203.0.113.0/30                          |  198.51.100.0/30
        |             [ISP-Router]                 |
        +---- G0/0/0 .2 ======= G0/0/1 .1 ---------+
                    (simulated internet)
```

The VPN peers are `203.0.113.1` ↔ `198.51.100.2`.

## Addressing

| Device     | Interface | IP address   | Mask            | Gateway     |
|------------|-----------|--------------|-----------------|-------------|
| FW-A       | G0/0/0    | 10.10.10.1   | 255.255.255.0   | —           |
| FW-A       | G0/0/1    | 203.0.113.1  | 255.255.255.252 | —           |
| ISP-Router | G0/0/0    | 203.0.113.2  | 255.255.255.252 | —           |
| ISP-Router | G0/0/1    | 198.51.100.1 | 255.255.255.252 | —           |
| FW-B       | G0/0/1    | 198.51.100.2 | 255.255.255.252 | —           |
| FW-B       | G0/0/0    | 10.20.20.1   | 255.255.255.0   | —           |
| PC-A1/A2   | Fa0       | 10.10.10.10 / .11 | 255.255.255.0 | 10.10.10.1 |
| PC-B1/B2   | Fa0       | 10.20.20.10 / .11 | 255.255.255.0 | 10.20.20.1 |

## What's configured (each VPN gateway)

**IKE Phase 1** — `crypto isakmp policy 10`: AES, SHA, pre-shared-key auth,
DH group 2, 86400s lifetime. Peers authenticate with a PSK bound to the
remote peer address.

**IPsec Phase 2** — transform set `ESP-AES-SHA` (`esp-aes esp-sha-hmac`,
tunnel mode), PFS group 2, bound via `crypto map VPN-MAP` on the outside
interface.

**Interesting traffic** — `access-list 100`: only `10.10.10.0/24 ↔
10.20.20.0/24` enters the tunnel. These are the VPN *selectors* (Palo Alto
calls them proxy IDs).

**NAT exemption** — `access-list 101` denies VPN traffic *before* the
permit: interesting traffic skips PAT entirely. Everything else from the
LAN is overloaded behind the outside address.

**Firewall policy** — extended ACL 110 inbound on the inside interface:
VPN traffic first, then web/DNS/ICMP egress, then `deny ip any any`.

> Lab crypto choices (AES/SHA/DH2) are what Packet Tracer supports.
> Production would use IKEv2, AES-256-GCM, SHA-256, DH14+. The concepts
> are identical — see [docs/VPN-CONCEPTS.md](docs/VPN-CONCEPTS.md).

## Repository contents

```
Lab-5-Site-to-Site-VPN-Firewall.pkt              # working lab
Lab-5-SCENARIO-1-Tunnel-Up-No-Traffic.pkt        # fault: firewall policy (data plane)
Lab-5-SCENARIO-2-Tunnel-Down.pkt                 # fault: PSK mismatch (control plane)
configs/
  fw-a.txt  fw-b.txt  isp.txt  sw-a.txt  sw-b.txt # paste-ready CLI
docs/
  VPN-CONCEPTS.md     # Cisco ↔ Palo Alto ↔ Fortinet concept map
  SCENARIO-1.md       # full investigation walkthrough
  SCENARIO-2.md       # full investigation walkthrough
scripts/
  build_topology.py   # regenerates all three .pkt files
```

## Quick start (10 minutes)

1. Open `Lab-5-Site-to-Site-VPN-Firewall.pkt` (Packet Tracer 8.2.1+), wait
   for links to converge.
2. From **PC-A1**: `ping 10.20.20.10`. The first ping triggers IKE —
   give it a few seconds.
3. On **FW-A**: `show crypto isakmp sa` → `QM_IDLE`. The tunnel is up.
4. `show crypto ipsec sa` → `pkts encaps` / `pkts decaps` counting. That
   is encrypted office-to-office traffic.
5. `show ip nat translations` → no entries for `10.10.10.x`↔`10.20.20.x`:
   NAT exemption working.

## The two scenarios

| # | File | Symptom | Layer | Investigate |
|---|------|---------|-------|-------------|
| 1 | `Lab-5-SCENARIO-1-Tunnel-Up-No-Traffic.pkt` | Tunnel up, ping fails | Data plane | selectors → NAT exemption → routes → **firewall policy** |
| 2 | `Lab-5-SCENARIO-2-Tunnel-Down.pkt` | No SAs at all | Control plane | peer reachability → Phase 1 → **authentication** → Phase 2 |

Full worked investigations: [docs/SCENARIO-1.md](docs/SCENARIO-1.md),
[docs/SCENARIO-2.md](docs/SCENARIO-2.md). Try them before reading.

## Build it yourself in Packet Tracer

1. Place: 3× ISR 4331, 2× 2960 switch, 4× PC-PT. Cable per the diagram
   (crossover between routers).
2. Paste `configs/fw-a.txt`, `configs/fw-b.txt`, `configs/isp.txt`,
   `configs/sw-a.txt`, `configs/sw-b.txt` into each CLI.
3. Set PC IPs from the addressing table.
4. Run the Quick start. Then break it: change one PSK character, or add a
   deny to a firewall ACL, and diagnose using the scenario guides.

## Regenerating the `.pkt` files

Built programmatically with the open-source
[`pt_codec`](https://github.com/w4lven/claude-to-packet-tracer) library:

```bash
git clone https://github.com/w4lven/claude-to-packet-tracer /tmp/ctt
python3 -m venv /tmp/ctt/.venv && /tmp/ctt/.venv/bin/pip install -r /tmp/ctt/requirements.txt
/tmp/ctt/.venv/bin/python scripts/build_topology.py
```

## Requirements

- Cisco Packet Tracer 8.2.1+ (encoded for 8.2.1; newer releases open it).
- Nothing else — everything is in this repo.

## Talking about this in interviews

- "Interesting traffic defines the selectors — only 10.10.10.0/24 to
  10.20.20.0/24 enters the tunnel. That's Palo Alto proxy IDs."
- "I exempt VPN traffic from NAT *before* the PAT line — translated
  selectors silently kill tunnels."
- "When a tunnel is up but traffic fails, I check the data plane, not
  crypto — I proved a firewall ACL was dropping post-decryption traffic
  with `show crypto ipsec sa` counters against ACL match counters."
- "When there's no SA at all, I go ordered: peer reachability, Phase 1
  proposals, authentication, Phase 2. The order is the skill."
