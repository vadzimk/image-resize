import {Outlet} from 'react-router-dom';

export default function Layout(){
    return(
        <div className="screen-height flex flex-row justify-center">
            <div className="flex flex-col justify-center">
                <Outlet/>
            </div>
        </div>
    )
}
