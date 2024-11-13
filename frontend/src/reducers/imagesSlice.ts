import {createAsyncThunk, createSlice, PayloadAction} from '@reduxjs/toolkit';
import {fetchWithHandler} from '../services/api.ts';
import {AppDispatch} from '../store.ts';

export type ImagesState = {
    filename?: string,
    object_prefix?: string,
    upload_link?: string,
}

export interface CreateProjectSchema {
    filename: string
}

export interface ProjectCreatedSchema extends CreateProjectSchema {
    object_prefix: string
    upload_link: string
}

export interface FastApiError {
    detail: string
}

export interface UploadFileS3Args {
    file: File,
    upload_link: string,
}

const initialState: ImagesState = {}


export const imagesSlice = createSlice({
    name: 'images',
    initialState,
    reducers: {},
    extraReducers: builder => {
        builder.addCase(getUploadLink.fulfilled, (state, action: PayloadAction<ProjectCreatedSchema>) => {
            return {...state, ...action.payload}
        })
    }
})

export const getUploadLink = createAsyncThunk<ProjectCreatedSchema, CreateProjectSchema, { rejectValue: FastApiError }>(
    '/images/new',
    async (imageFileFields: CreateProjectSchema, thunkAPI) => {
        return await fetchWithHandler(
            '/api/images',
            {
                method: 'POST',
                body: JSON.stringify(imageFileFields)
            },
            thunkAPI.dispatch as AppDispatch,
            thunkAPI.rejectWithValue,
            "Could not request new upload url"
        )
    }
)

export const uploadFileS3 = createAsyncThunk<'', UploadFileS3Args>(
    '/images/uploadS3',
    async (args: UploadFileS3Args, thunkAPI) => {
        return await fetchWithHandler(
            args.upload_link,
            {
                method: 'PUT',
                body: args.file,
                headers: {
                    "Content-Type": 'application/octet-stream'
                },
            },
            thunkAPI.dispatch as AppDispatch,
            thunkAPI.rejectWithValue,
            'Could not upload file ' + args.file.name
        )
    }
)


export default imagesSlice
