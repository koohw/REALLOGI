import MyComponent from './MyComponents';
import Counter from './Counter';
import './App.css';

import React, { Fragment } from 'react';

const App = () => {
  return (
    <Fragment>
      <MyComponent>리액트</MyComponent>
      <Counter />
    </Fragment>
  );
};


export default App;
