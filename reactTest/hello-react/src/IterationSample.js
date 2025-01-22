import { useState } from "react";

const IterationSample = () => {
    const [names, setNames ] = useState([
        { id: 1, text: '눈사람' },
        { id: 2, text: '얼음' },
        { id: 3, text: '눈' },
        { id: 4, text: '바람' }
    ]);
    const [inputText, setInputText] = useState('');
    const [nextId, setNextId] = useState(5); // 새로운 항목을 추가할 때 사용할 id   


    const onChange = e => setInputText(e.target.value);
    const onClick = () => {
        const nextNames = names.concat({
            id: nextId,
            text: inputText
        });
        setNextId(nextId + 1); // nextId 값에 1을 더해줍니다.
        setNames(nextNames); // names 값을 업데이트합니다.
        setInputText(''); // inputText를 비웁니다.
    }

    const namesList = names.map(name => <li key={name.id}>{name.text}</li>);

    return (
    <div>
        <input value={inputText} onChange={onChange} />
        <button onClick={onClick}>추가</button>
        <ul>{namesList}</ul>
    </div>
    );
};
export default IterationSample;