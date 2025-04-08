export interface CodeInjection {
    code: string;
}

const interceptors: Map<string, InvocationListener> = new Map();

export function intercept(address: string, codeInjection: CodeInjection): void {
    detachInterception(address);

    const interceptor = Interceptor.attach(ptr(address), function () {
        try {
            eval(codeInjection.code);
        } catch (error) {
            console.error(`Error executing injected code at ${address}:`, error);
        }
    });
    interceptors.set(address, interceptor);
}

export function detachInterception(address: string): void {
    const interceptor = interceptors.get(address);
    if (interceptor) {
        interceptor.detach();
        interceptors.delete(address);
    }
}

export function detachAllInterceptors(): void {
    for (const [address, interceptor] of interceptors.entries()) {
        interceptor.detach();
    }
    interceptors.clear();
}