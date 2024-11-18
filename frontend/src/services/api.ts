// import {NotificationType, notify} from '../reducers/notificationSlice.ts';
// import {UserState} from '../reducers/types';
// import {AppDispatch, RootState} from '../store.ts';


export interface FastApiError {
    detail: string
}

export async function fetchWithHandler<T>(
    url: string,
    options: RequestInit,
    // dispatch: AppDispatch,
    rejectWithValue: (value: FastApiError) => any,
    // errorMessage: string
): Promise<T | ReturnType<typeof rejectWithValue>> {
    const isFormData = options.body instanceof FormData
    try {
        const res = await fetch(
            url,
            {
                ...options,
                headers: {
                    ...(isFormData ? {} : {"Content-Type": "application/json"}),
                    ...options.headers,
                },
            })

        if (!res.ok) {
            const errorData: FastApiError = await res.json()
            // dispatch(notify({message: errorMessage, type: NotificationType.ERROR}))
            console.error(errorData.detail)
            return rejectWithValue(errorData)
        }

        const contentType: string | null = res.headers.get('Content-Type')
        if (contentType?.startsWith('application/json')) {
            return await res.json() as T
        } else {
            // handle as text
            return await res.text() as unknown
        }
    } catch (e) {
        const err = e as Error
        console.error('An error occurred: ', err)
        // dispatch(notify({message: errorMessage, type: NotificationType.ERROR}))
        return rejectWithValue({detail: err.message})
    }
}

// export async function fetchWithAuthHandler<T>(
//     url: string,
//     options: RequestInit,
//     getState: () => RootState,
//     dispatch: AppDispatch,
//     rejectWithValue: (value: FastApiError) => any,
//     errorMessage: string
// ) {
//     const state = getState() as { user: UserState }
//     const token = state.user.access_token
//     return await fetchWithHandler<T>(
//         url,
//         {
//             ...options,
//             headers: {
//                 "Authorization": `Bearer ${token}`,
//                 ...options.headers,
//             }
//         },
//         dispatch,
//         rejectWithValue,
//         errorMessage
//     )
// }
