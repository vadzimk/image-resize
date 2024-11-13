import RoundPlus from './icons/RoundPlus.tsx';
import React, {useRef, useState} from 'react';
import {useAppDispatch} from '../hooks.ts';
import {getUploadLink, uploadFileS3} from '../reducers/imagesSlice.ts';
import {useNavigate} from 'react-router-dom';

export default function ImageUpload() {
    const [isDragging, setIsDragging] = useState(false)
    const fileInputRef = useRef<HTMLInputElement | null>(null)
    const dispatch = useAppDispatch() // ts setup requires typed dispatch
    const navigate = useNavigate()
    const handleButtonClick = () => {
        fileInputRef.current?.click()
    }

    const sendFile = async (file?: File) => {
        if (!file) {
            console.error('No file provided')
            return
        }
        try {
            const projectCreatedResponse = await dispatch(getUploadLink({filename: file.name})).unwrap()
            // console.log("projectCreatedResponse", projectCreatedResponse)
            await dispatch(uploadFileS3({file, upload_link: projectCreatedResponse.upload_link})).unwrap() // returns empty string if ok
            // console.log('navigating to /progress')
            navigate('/progress')
        } catch {
            /* empty */
        }
    }

    const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0]
        // console.log('Selected', file?.name)
        await sendFile(file)
    }

    const handleDragOver = (event: React.DragEvent<HTMLInputElement>) => {
        event.preventDefault()
        setIsDragging(true)
    }

    const handleDragLeave = () => {
        setIsDragging(false)
    }

    const handleDrop = async (event: React.DragEvent<HTMLDivElement>) => {
        event.preventDefault()
        setIsDragging(false)
        const file = event.dataTransfer.files?.[0]
        // console.log('Dropped file', file?.name)
        await sendFile(file)
    }


    return (
        <div className="flex flex-col">
            <div>
                <h2 className="text-2xl text-center mb-8">Upload Image</h2>
            </div>
            <div
                className={`border rounded-3xl border-slate-400 ${isDragging ? 'bg-accent' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
            >
                <div className="m-8 mx-20">
                    <button
                        className="btn btn-lg h-20 w-20 btn-primary rounded-3xl"
                        onClick={handleButtonClick}
                    >
                        <RoundPlus className="w-16 h-16"/>
                    </button>
                </div>
            </div>
            <input
                type="file"
                ref={fileInputRef}
                className="hidden"
                onChange={handleFileChange}
                accept="image/*"
            />
        </div>
    )
}
