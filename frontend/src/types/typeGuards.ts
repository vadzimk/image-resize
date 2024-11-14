// type-guard functions
import {ImageVersion, OnSubscribeSchema, ProjectProgressSchema, TaskState} from './processingStatusTypes';

export function isOnSubscribeSchema(message: any): message is OnSubscribeSchema {
    return (
        typeof message === 'object' &&
        message !== null &&
        ["SUBSCRIBE", "UNSUBSCRIBE"].includes(message.action) &&
        typeof message.object_prefix === 'string' &&
        typeof message.status_code === 'number' &&
        typeof message.status === 'string' &&
        (typeof message.message === 'string' || message.message === null)
    )
}

export function isProjectProgressSchema(message: any): message is ProjectProgressSchema {
    return (
        typeof message === 'object' &&
        message !== null &&
        typeof message.object_prefix === 'string' &&
        Object.values(TaskState).includes(message.state) &&
        typeof message.versions === 'object' &&
        message.versions !== null &&
        // only check existing keys in message.versions to ensure they match the type string
        Object.keys(message.versions).every(
            key => Object.values(ImageVersion).includes(key as ImageVersion) &&
                typeof message.versions[key as ImageVersion] === 'string'
        ) &&
        typeof message.progress === 'object' &&
        message.progress !== null &&
        typeof message.progress.done === 'number' &&
        typeof message.progress.total === 'number'
    )
}
