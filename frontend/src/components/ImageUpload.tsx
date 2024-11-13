import RoundPlus from './icons/RoundPlus.tsx';
import React, {useRef, useState} from 'react';
import {useAppDispatch} from '../hooks.ts';
import {getUploadLink} from '../reducers/imagesSlice.ts';

export default function ImageUpload() {
    const [isDragging, setIsDragging] = useState(false)
    const fileInputRef = useRef<HTMLInputElement | null>(null)
    const dispatch = useAppDispatch() // ts setup requires typed dispatch

    const handleButtonClick = () => {
        fileInputRef.current?.click()
    }

    const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0]
        if (file) {
            console.log('Selected', file.name)
            await dispatch(getUploadLink({filename: file.name}))
        }
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
        if (file) {
            console.log('Dropped file', file.name)
            await dispatch(getUploadLink({filename: file.name}))
        }
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
