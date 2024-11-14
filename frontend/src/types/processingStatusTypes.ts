export interface OnSubscribeSchema {
    action: "SUBSCRIBE" | "UNSUBSCRIBE"
    object_prefix: string
    status_code: number
    status: string
    message: string | null
}

export enum TaskState {
    EXPECTING_ORIGINAL = "EXPECTING_ORIGINAL",
    GOT_ORIGINAL = "GOT_ORIGINAL",
    STARTED = "STARTED",
    PROGRESS = "PROGRESS",
    SUCCESS = "SUCCESS",
    FAILURE = "FAILURE",
    REVOKED = "REVOKED",
}

export enum ImageVersion {
    original = "original",
    thumb = "thumb",
    big_thumb = "big_thumb",
    big_1920 = "big_1920",
    d2500 = "d2500",
}

export interface Progress {
    done: number
    total: number
}

export interface ProjectProgressSchema {
    object_prefix: string
    state: TaskState
    versions: Record<ImageVersion, string>
    progress: Progress
}
