import {useAppSelector} from '../hooks.ts';

export default function ProcessingStatus() {
    const filename = useAppSelector(state => state.images.filename)
    // console.log(filename?.length)
    const F_CONTAINER_LIM = 36
    const F_PART_ONE_LIM = 26
    const F_PART_TWO_LIM = F_CONTAINER_LIM - F_PART_ONE_LIM

    return (
        <div className="flex flex-col bg-primary bg-opacity-15 rounded-3xl p-12">
            <div className="text-2xl text-center mb-8">Processing</div>
            <p className="mb-8">
                {filename?.substring(0, filename?.length > F_CONTAINER_LIM ? F_PART_ONE_LIM : filename?.length - F_PART_TWO_LIM )}
                {filename && filename.length > F_CONTAINER_LIM ? ' ... ' : ''}
                {filename?.substring(filename?.length-F_PART_TWO_LIM)}
            </p>
            <progress className="progress progress-primary w-full" value="70" max="100"></progress>
            <button className="btn btn-sm btn-ghost mt-20">
                Cancel
            </button>
        </div>
    )
}
