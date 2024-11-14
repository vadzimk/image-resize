import {useDispatch, useSelector, useStore} from 'react-redux'
import type {AppDispatch, AppStore, RootState} from './store'
import {useEffect} from 'react';
import {useNavigate} from 'react-router-dom';

// typed hooks
// form https://redux.js.org/usage/usage-with-typescript#standard-redux-toolkit-project-setup-with-typescript
// Use throughout your app instead of plain `useDispatch` and `useSelector`
export const useAppDispatch = useDispatch.withTypes<AppDispatch>()
export const useAppSelector = useSelector.withTypes<RootState>()
export const useAppStore = useStore.withTypes<AppStore>()

// custom hooks
export const usePreventBackNavigation = () => {
    // prevent navigate back
    useEffect(() => {
        window.history.pushState(null, '', window.location.href) // push same location to history

        const handlePopState = () => { // intercept popstate event
            window.history.pushState(null, '', window.location.href)
        }
        window.onpopstate = handlePopState // back button event listener
        return () => {
            window.onpopstate = null
        }
    }, []);
}

export const useReplaceBackNavigation = (path: string) => {
    /*
    * Replaces last location in history to navigate to with provided path
    * @param path: url path to navigate to when browser back button in clicked
    * */
    const navigate = useNavigate()

    useEffect(() => {
         window.history.pushState(null, '', window.location.href) // push same location to history

        const handlePopState = () => {
            navigate(path, {replace: true})
        }
        window.onpopstate = handlePopState

        return () => {
            window.onpopstate = null
        }
    }, [navigate, path]);
}
