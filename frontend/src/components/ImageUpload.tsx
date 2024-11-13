import RoundPlus from './icons/RoundPlus.tsx';

export default function ImageUpload() {
    return (
        <div className="flex flex-col">
            <div>
                <h2 className="text-2xl text-center mb-8">Upload Image</h2>
            </div>
            <div className="border rounded-3xl border-slate-400">
                <div className="m-8 mx-20">
                    <button className="btn btn-lg h-20 w-20 btn-primary rounded-3xl">
                        <RoundPlus className="w-16 h-16"/>
                    </button>
                </div>
            </div>
        </div>
    )
}
