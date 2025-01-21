import React, { Component } from "react";

class Hello extends Component {
  render() {
    const { color, name = "이름없음", isSpecial } = this.props;
    return (
      <div style={{ color }}>
        {isSpecial && <b>*</b>}
        안녕하세요 {name}
      </div>
    );
  }
}

export default Hello;
