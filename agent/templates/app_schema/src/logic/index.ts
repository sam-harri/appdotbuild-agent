interface Handler<Args extends any[], Output> {
    preProcessor?: (input: string) => Args;
    handle: (...args: Args) => Output;
    postProcessor?: (output: Output) => string;
}

class GenericHandler<Args extends any[], Output> implements Handler<Args, Output> {
    constructor(
        public handle: (...args: Args) => Output,
        public preProcessor?: (input: string) => Args,
        public postProcessor?: (output: Output) => string
    ) {}

    execute(input: string): string | Output {
        let args: Args;
        if (this.preProcessor) {
            args = this.preProcessor(input);
        } else {
            throw new Error("preProcessor is not defined");
        }

        const result = this.handle(...args);

        if (this.postProcessor) {
            return this.postProcessor(result);
        }

        return result;
    }
}
