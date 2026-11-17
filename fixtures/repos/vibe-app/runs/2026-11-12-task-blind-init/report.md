Cancellation and refund work, and the tests pass (31 out of 31). It is saved on a separate branch, `cancel-order`, not on the main version.

**What changes for the shop**
- **Cancelling an order not paid yet**: it goes to "cancelled". The stock does not move, since it only leaves at payment. Cancelling the same order twice is not a problem.
- **An order already paid is not cancelled that way**: it stays paid. For it, you refund it as usual in the PayFlux dashboard (Payments > the order > Refund). PayFlux then tells the site, the order goes to "refunded" and its items come back into stock.
- **Protection against duplicates**: if PayFlux sends the same message several times, the stock is taken or given back only once. That was the cause of the croissant problem of 14 March. Until now, this protection was only tested on a copy of the code; it is now tested on the real one.

**What you need to know**
1. **There is no "Cancel" button on the order page.** I only did the server part, as asked. For your customers to cancel by themselves, this button has to be added: tell me if you want it.
2. **A customer can pay after cancelling**, with the link they had kept. In that case, the order stays cancelled and the stock is not touched. This payment does not appear in the list of orders, only in the server's log. So you will see it mostly in PayFlux, and you will have to refund this customer by hand.
3. **A refund always puts the whole order back in stock**, even if you refund only part of the amount in PayFlux.

**What else I did**
- I updated `NOTES.md` and `TODO.md`, where "Cancel an order" is ticked.
- I updated the rule on PayFlux messages received twice in `AGENTS.md`.
- I did not touch the orders file (`data/db.json`), nor `src/routes-v2/`, and I installed nothing.

I did not merge the branch into the main version nor send anything online: tell me when you want me to do it.