import {useAppSelector, useReplaceBackNavigation} from '../hooks.ts';
import {ImageVersion} from '../types';

export default function Result() {
    useReplaceBackNavigation('/')

    const versionNamesMap = {
        [ImageVersion.original]: 'Original',
        [ImageVersion.thumb]: 'Thumb 150 x 120',
        [ImageVersion.big_thumb]: 'BigThumb 700 x 700',
        [ImageVersion.big_1920]: 'Big 1920 x 1080',
        [ImageVersion.d2500]: '2500 x 2500',
    }

    const {filename, versions} = useAppSelector(state => state.projects.slice(-1)[0])
    return (
        <div className="flex flex-col">
            <h3 className="text-xl text-center mb-8 font-bold">{filename}</h3>
            <div className="flex flex-col m-auto">
                {
                    versions && Object.entries(versions).map(([key, value]) => (
                        <a
                            href={value}
                            key={value}
                            className="my-2 text-primary"
                        >
                            {versionNamesMap[key as ImageVersion]}
                        </a>
                    ))
                }
            </div>
        </div>
    )
}
