import {createAsyncThunk, createSlice, PayloadAction} from '@reduxjs/toolkit';
import {fetchWithHandler} from '../services/api.ts';
import {AppDispatch} from '../store.ts';
import {ImageVersion, ProjectProgressSchema, TaskState} from '../types';

export interface FastApiError {
    detail: string
}

export interface UploadFileS3Args {
    file: File,
    upload_link: string,
}

export interface CreateProjectSchema {
    filename: string
}

export interface ProjectCreatedSchema extends CreateProjectSchema {
    object_prefix: string
    upload_link: string
}

interface GetProjectSchema {
    object_prefix: string
    state: TaskState
    versions: Record<ImageVersion, string>
}


type ProjectState = Partial<GetProjectSchema & ProjectCreatedSchema> // combination of fields form both interfaces, making all fields optional

const initialState: ProjectState[] = []


export const projectsSlice = createSlice({
    name: 'projects',
    initialState,
    reducers: {
        projectStateUpdated: function (state, action: PayloadAction<ProjectProgressSchema>) {
            return state.map(item =>
                item.object_prefix === action.payload.object_prefix ?
                    {...item, ...action.payload} : item
            )
        }
    },
    extraReducers: builder => {
        builder.addCase(getUploadLink.fulfilled, (state, action: PayloadAction<ProjectCreatedSchema>) => {
            const newProject = {...action.payload}
            return [...state, newProject]
        })
    }
})

export const getUploadLink = createAsyncThunk<ProjectCreatedSchema, CreateProjectSchema, { rejectValue: FastApiError }>(
    '/projects/new',
    async (imageFileFields: CreateProjectSchema, thunkAPI) => {
        return await fetchWithHandler(
            '/api/images',
            {
                method: 'POST',
                body: JSON.stringify(imageFileFields)
            },
            thunkAPI.dispatch as AppDispatch,
            // thunkAPI.rejectWithValue,
            // "Could not request new upload url"
        )
    }
)

export const uploadFileS3 = createAsyncThunk<'', UploadFileS3Args>(
    '/projects/uploadS3',
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
            // thunkAPI.rejectWithValue,
            // 'Could not upload file ' + args.file.name
        )
    }
)

export const {projectStateUpdated} = projectsSlice.actions

export default projectsSlice
