Milestone 11 is about adding the first broker boundary, likely starting with paper trading, not real-money trading.

  High level:

  - Define an ADR first for how broker/execution integration should work.
  - Probably use Alpaca paper trading as the first broker adapter.
  - Let the system take an existing approved OrderIntent and send it to a paper broker.
  - Bring paper execution results back into the system as recorded fills/position updates.
  - Keep the local JSON store as the source for your internal trade records.
  - Preserve the boundary that broker data is external execution fact, not trade meaning.

  What it is not:

  - Not real-money trading yet.
  - Not autonomous trading.
  - Not broker-driven recommendations.
  - Not replacing your judgment.
  - Not a full order management system.

  The point is: after Milestone 10 made credentials safer, Milestone 11 starts connecting the disciplined workflow to a paper execution environment while keeping everything human-controlled and auditable.

