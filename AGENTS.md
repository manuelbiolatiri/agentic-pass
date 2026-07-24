# AGENTS.md — Mandate

Standing instructions for every agent working in this workspace. Read fully before
starting any task.

## What this project is

A delegated authorisation layer for AI agents acting on behalf of humans, applied to
wallet passes (tickets, memberships, access credentials). An agent can request a pass
on a person's behalf only when it holds a signed, scoped, proof-of-possession-bound
mandate from that person.

---

## The seven invariants

These are not preferences. Code that violates one of these is wrong, however elegant.
If a task appears to require breaking one, **stop and ask** rather than choosing.

1. **`sub` is always the human principal. The agent is always `act`. Never the reverse.**
   An agent may acquire; it may never become the holder.
2. **Mandates are proof-of-possession bound via `cnf`. Never bearer.**
   A mandate presented without a matching key proof is rejected.
3. **Scope comes only from the signed token. Never from the request body.**
   The enforcement point must not read `authorization_details` from anywhere else.
4. **Idempotency keys on `(mandate_jti, canonical_request_hash)`.**
   Not on a client-supplied key. Replays return the stored outcome, including stored
   denials, without re-evaluation.
5. **Every decision path terminates in an audit record.** Allow, deny, escalate, error.
   There is no branch that returns without writing one first.
6. **Escalation timeouts fail closed.** A pending approval that expires is a denial.
7. **Profile existing standards. Invent nothing.**
   RFC 8693 for delegation, `cnf` for PoP, CIBA for human-in-the-loop,
   draft-klrc-aiagent-auth for the overall model. If a bespoke format seems necessary,
   stop and ask.
