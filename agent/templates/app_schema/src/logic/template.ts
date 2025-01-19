import { db } from "../db";
import { messagesTable, usersTable } from "../db/schema/common";
import { Handler, GenericHandler, Message } from "../common/handler";

export const putMessage = async (user_id: string, role: 'user' | 'assistant', content: string) => {
    await db.insert(usersTable).values({ id: user_id }).onConflictDoNothing();
    await db.insert(messagesTable).values({ user_id, role, content });
}