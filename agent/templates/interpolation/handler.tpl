import { Message, GenericHandler } from "../common/handler";
import { client } from "../common/llm";
const nunjucks = require('nunjucks');
import { {% for type in typescript_schema_type_names %} {{type}}, {% endfor %} } from "../common/schema";

{{handler}}

const preProcessorPrompt = `
Examine conversation between user and assistant and extract structured arguments for a function.

<instructions>
{{instructions}}
</instructions>

Examples:

{% for example in examples %}
Input:
{{ example[0] }}
Output:
{{ example[1] }}
{% endfor %}

Conversation:{% raw %}
{% for message in messages %}
<role name="{{message.role}}">{{message.content}}</role>
{% endfor %}{% endraw %}
`;

const preProcessor = async (input: Message[]): Promise<Options> => {
    const userPrompt = nunjucks.renderString(preProcessorPrompt, { messages: input });
    const response = await client.messages.create({
        model: 'anthropic.claude-3-5-sonnet-20241022-v2:0',
        max_tokens: 2048,
        messages: [{ role: 'user', content: userPrompt }, { role: 'assistant', content: '{'}]
    });
    switch (response.content[0].type) {
        case "text":
            const fullResponse = '{' + response.content[0].text;
            const jsonResponse = fullResponse.match(/{([^}]*)}/)![0];
            return JSON.parse(jsonResponse!);
        default:
            throw new Error("Unexpected response type");
    }
};

const postProcessorPrompt = `
Generate response to user using output from {{handler_name}} function and conversation.

{% raw %}{{output}}{% endraw %}

Conversation:{% raw %}
{% for message in messages %}
<role name="{{message.role}}">{{message.content}}</role>
{% endfor %}{% endraw %}
`

const postProcessor = async (output: object, input: Message[]): Promise<Message[]> => {
    const assistantPrompt = nunjucks.renderString(postProcessorPrompt, { output, messages: input });
    const response = await client.messages.create({
        model: 'anthropic.claude-3-5-sonnet-20241022-v2:0',
        max_tokens: 2048,
        messages: [{ role: 'user', content: assistantPrompt }]
    });
    switch (response.content[0].type) {
        case "text":
            return [{ role: 'assistant', content: response.content[0].text }];
        default:
            throw new Error("Unexpected response type");
    }
};

export const {{handler_name}} = new GenericHandler(handle, preProcessor, postProcessor);
