import { randomUUID } from "node:crypto";
import { createServer } from "node:http";
import { createApp } from "./http.ts";
import { createTicketService } from "./tickets/service.ts";
import { TicketStore } from "./tickets/store.ts";

const service = createTicketService({ store: new TicketStore(), now: () => new Date(), newId: randomUUID });
const port = Number(process.env.PORT ?? 3001);
createServer(createApp(service)).listen(port, () => console.log(`deskly api on :${port}`));
