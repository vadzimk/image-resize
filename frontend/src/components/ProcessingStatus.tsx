import {useAppDispatch, useAppSelector} from '../hooks.ts';
import useWebSocket, {ReadyState} from 'react-use-websocket';
import {useEffect, useState} from 'react';
import {isProjectProgressSchema, TaskState} from '../types'
import {useNavigate} from 'react-router-dom';
import {usePreventBackNavigation} from '../hooks';
import {projectStateUpdated} from '../reducers/projectsSlice.ts';


export default function ProcessingStatus() {
    // Set protocols in useWebSocket only if your WebSocket requires specific subprotocols; otherwise, it can be omitted.
    const {lastJsonMessage, readyState, sendJsonMessage} = useWebSocket('/ws', {share: true}) // in dev using vite proxy
    const projects = useAppSelector(state => state.projects)
    const {filename, object_prefix}  = projects.slice(-1)[0] // get last item
    const [progressValue, setProgressValue] = useState<number>(0)
    const navigate = useNavigate()
    const dispatch = useAppDispatch()

    usePreventBackNavigation()

    // subscribe to watch progress
    useEffect(() => {
        if (readyState === ReadyState.OPEN && object_prefix) {
            sendJsonMessage({"action": "SUBSCRIBE", "object_prefix": object_prefix})
        }
    }, [readyState, sendJsonMessage, object_prefix])

    // watch progress value
    useEffect(() => {
        if (lastJsonMessage !== null) {
            if (isProjectProgressSchema(lastJsonMessage)) {
                dispatch(projectStateUpdated(lastJsonMessage))
                setProgressValue(lastJsonMessage.progress.done / lastJsonMessage.progress.total * 100)
                if (lastJsonMessage.progress.done === lastJsonMessage.progress.total &&
                    lastJsonMessage.state === TaskState.SUCCESS) {
                    navigate('/result')
                }
            }
        }
    }, [lastJsonMessage, navigate, dispatch]);


    const handleCancel = () => {
        console.error('NotImplementedError')
        navigate('/')
    }

    const F_CONTAINER_LIM = 26
    const F_PART_ONE_LIM = 16
    const F_PART_TWO_LIM = F_CONTAINER_LIM - F_PART_ONE_LIM
    return (
        <div className="flex flex-col bg-primary bg-opacity-15 rounded-3xl p-12">
            <h2 className="text-2xl text-center mb-8">Processing</h2>
            <p className="mb-8">
                {filename?.substring(0, filename?.length > F_CONTAINER_LIM ? F_PART_ONE_LIM : filename?.length - F_PART_TWO_LIM)}
                {filename && filename.length > F_CONTAINER_LIM ? ' ... ' : ''}
                {filename?.substring(filename?.length - F_PART_TWO_LIM)}
            </p>
            <progress className="progress progress-primary w-full" value={progressValue} max="100"></progress>
            <button
                className="btn btn-sm btn-ghost mt-20"
                onClick={handleCancel}
            >
                Cancel
            </button>
        </div>
    )
}
