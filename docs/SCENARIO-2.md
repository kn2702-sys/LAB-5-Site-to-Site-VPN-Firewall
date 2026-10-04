# Scenario 2: Tunnel doesn't establish

**File:** `Lab-5-SCENARIO-2-Tunnel-Down.pkt`

**Symptom.** PC-A1 cannot ping PC-B1, and this time the tunnel itself is
missing.

**The rule for this scenario:** with no SAs, the data plane is irrelevant.
Investigate the control plane — in this order:

```
peer reachability → Phase 1 params → authentication → Phase 2 params
```

---

## 1. Peer reachability — can the gateways even see each other?

**Where:** FW-A.

```
ping 198.51.100.2
```

**Expect:** replies — the underlay (ISP transit) is fine.

**Result here:** ✅ reachable. This kills a whole category of theories
(ISP outage, wrong next-hop, interface down) in ten seconds. If it had
failed, you'd work it like any underlay problem: `show ip interface
brief`, `show ip route`, then the ISP — *before* ever looking at crypto.

## 2. Tunnel state — confirm what "down" means

```
show crypto isakmp sa
```

**Result here:** ❌ empty. No Phase 1 SA exists.

```
show crypto ipsec sa
```

**Result here:** ❌ empty too, as expected — Phase 2 can't happen without
Phase 1.

So: the gateways can reach each other, but IKE won't talk. That narrows it
to three suspects: Phase 1 parameters, authentication, Phase 2 parameters.

## 3. Phase 1 parameters — do both ends propose the same thing?

**Where:** both FW-A and FW-B.

```
show crypto isakmp policy
```

**Expect (both sides):**

```
Priority 10: aes, sha, pre-share, DH group 2, lifetime 86400
```

**Result here:** ✅ identical. If these differed (e.g. one side `3des`
while the other offers `aes`), Phase 1 fails at proposal — the classic
"we upgraded one end on Friday" outage.

## 4. Authentication — the pre-shared key

**Where:** both routers.

```
show running-config | include crypto isakmp key
```

**FW-A shows:**

```
crypto isakmp key C1sco12345 address 198.51.100.2
```

**FW-B shows:**

```
crypto isakmp key WrongKey999 address 203.0.113.1
```

**Result here:** ❌ **mismatch found.** The keys differ, so IKE
authentication fails and Phase 1 never completes. This is the single most
common real-world cause of "tunnel won't come up" — a typo during a key
rotation, or one end updated and the other forgotten.

## 5. Phase 2 parameters — check anyway, build the habit

```
show crypto ipsec transform-set
show crypto map
```

**Result here:** ✅ transform sets (`ESP-AES-SHA`, tunnel mode, PFS
group 2) and crypto map entries mirror each other. Worth the 30 seconds:
a Phase 2 mismatch produces a *different* symptom (Phase 1 up, Phase 2
fails — a hybrid of Scenarios 1 and 2), and you want to recognize it.

## The fix

On **FW-B**:

```
configure terminal
crypto isakmp key C1sco12345 address 203.0.113.1
end
```

Then generate interesting traffic from PC-A1:

```
ping 10.20.20.10
```

The ping triggers IKE; verify:

```
show crypto isakmp sa     →  QM_IDLE  ✅
show crypto ipsec sa      →  encaps/decaps growing  ✅
```

## The takeaway

"No tunnel" has a short suspect list, and it's *ordered*: reachability
first (underlay), then Phase 1 proposals, then authentication, then Phase 2.
Checking the PSK before confirming reachability is how you spend an hour
fixing the wrong layer. The order is the skill.
