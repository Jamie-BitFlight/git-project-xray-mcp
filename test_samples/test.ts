// TypeScript test file
import { EventEmitter } from 'events';
import type { Request, Response } from 'express';

// Interface
interface User {
    id: number;
    name: string;
    email: string;
}

// Type alias
type UserRole = 'admin' | 'user' | 'guest';

// Enum
enum Status {
    Active = 'ACTIVE',
    Inactive = 'INACTIVE',
    Pending = 'PENDING'
}

// Abstract class
abstract class BaseService {
    protected apiUrl: string;
    
    constructor(apiUrl: string) {
        this.apiUrl = apiUrl;
    }
    
    abstract fetchData<T>(): Promise<T>;
}

// Generic class
class UserService extends BaseService {
    private users: Map<number, User>;
    
    constructor(apiUrl: string) {
        super(apiUrl);
        this.users = new Map();
    }
    
    async fetchData<User>(): Promise<User> {
        // Implementation
        return {} as User;
    }
    
    addUser(user: User): void {
        this.users.set(user.id, user);
    }
    
    getUser(id: number): User | undefined {
        return this.users.get(id);
    }
}

// Function with type annotations
function processUsers(users: User[], role: UserRole): User[] {
    return users.filter(user => {
        // Some filtering logic
        return true;
    });
}

// Namespace
namespace Utils {
    export function formatDate(date: Date): string {
        return date.toISOString();
    }
    
    export class Logger {
        log(message: string): void {
            console.log(message);
        }
    }
}

// Type guard
function isUser(obj: any): obj is User {
    return obj && typeof obj.id === 'number' && typeof obj.name === 'string';
}

export { UserService, processUsers, Status, Utils };
export type { User, UserRole };