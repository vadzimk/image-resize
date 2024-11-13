import {useRouteError} from 'react-router-dom';

interface ErrorType {
    message?: string;
    statusText?: string;
}

export default function ErrorPage() {
    const error = useRouteError() as ErrorType;
    console.error(error);
    return (
        <div className="flex flex-col items-center justify-center h-screen p-5">
            <h1>Ah...</h1>
            <p>Got an error</p>
            <p>{error.statusText || error.message}</p>
        </div>
    );
}
