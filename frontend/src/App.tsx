import './index.css'
import {createBrowserRouter, RouterProvider} from 'react-router-dom';
import Layout from './Layout.tsx';
import ErrorPage from './pages/ErrorPage.tsx';
import Home from './pages/Home.tsx';
import Progress from './components/Progress.tsx';

const router = createBrowserRouter([
    {
        path: '/',
        element: <Layout/>,
        errorElement: <ErrorPage/>,
        children: [
            {index: true, element: <Home/>},
            {path: 'progress', element: <Progress/>}
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
