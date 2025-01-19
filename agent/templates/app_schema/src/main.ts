import { handlers } from "./logic";
import { FunctionDef, getRoute } from "./logic/router";
import { getHistory, putMessage } from "./common/crud";
import 'dotenv/config';
const { Context, Telegraf } = require('telegraf');
const { message } = require('telegraf/filters');

const functions: FunctionDef[] = [
    { name: 'dummy', description: 'catch-all function that just gets plain response from LLM' },
]

const mainHandler = async (ctx: typeof Context) => {
    await putMessage(ctx.from!.id.toString(), 'user', ctx.message.text!);
    const messages = await getHistory(ctx.from!.id.toString(), 3);
    const validMessages = messages.filter(msg => msg.role !== null && msg.content !== null) as { role: "user" | "assistant"; content: string }[];
    const route = await getRoute(validMessages, functions);
    const handler = handlers[route];
    const result = await handler.execute(validMessages);
    if (result[0].role === "assistant") {
        ctx.reply(result[0].content);
        await putMessage(ctx.from!.id.toString(), 'assistant', result[0].content);
    }
}

const bot = new Telegraf(process.env.BOT_TOKEN);
bot.on(message('text'), mainHandler);
bot.launch();

// Enable graceful stop
process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));

/* import { dummyHandler } from "./logic/dummy_handler";
import { Message } from "./common/handler";

// Sample input
const messages: Message[] = [
    { role: 'user', content: 'Hello' },
];

// Execute the handler
dummyHandler.execute(messages).then((result) => {
    console.log(result);
}).catch(console.error); */