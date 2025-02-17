import './index.css'
import {createBrowserRouter, RouterProvider} from 'react-router-dom';
import Layout from './Layout.tsx';
import ErrorPage from './pages/ErrorPage.tsx';
import Home from './pages/Home.tsx';
import ProcessingStatus from './components/ProcessingStatus.tsx';
import Result from './components/Result.tsx';

const router = createBrowserRouter([
    {
        path: '/',
        element: <Layout/>,
        errorElement: <ErrorPage/>,
        children: [
            {index: true, element: <Home/>},
            {path: 'progress', element: <ProcessingStatus/>},
            {path: 'result', element: <Result/>}
        ]
    }
])

function App() {

    return (
        <>
            <RouterProvider router={router}/>
        </>
    )
}

export default App
