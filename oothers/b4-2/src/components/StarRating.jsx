/**
 * ============================================================
 * StarRating.jsx — 별점 입력/표시 컴포넌트
 * ============================================================
 * 
 * 1~5점까지 별(★)을 표시하고, 클릭하여 점수를 선택할 수 있습니다.
 * 
 * [이벤트 → 상태 → 렌더링 흐름]
 *   별을 클릭(이벤트) → onChange로 점수 변경(상태) → 별 아이콘 업데이트(렌더링)
 *   이것이 미션에서 요구하는 "상태 변경이 렌더링 변화로 이어지는 지점"의 좋은 예입니다.
 * 
 * props:
 *   - value: 현재 별점 (1~5)
 *   - onChange: 별점이 변경될 때 호출 (선택 모드에서만)
 *   - readOnly: true이면 표시만, false이면 클릭으로 변경 가능
 *   - size: 별 크기 ('small', 'medium', 'large')
 */

import { useState } from 'react';
import './StarRating.css';

export default function StarRating({
  value = 0,           // 현재 별점
  onChange,            // 별점 변경 콜백
  readOnly = false,    // 읽기 전용 여부
  size = 'medium',     // 크기
}) {
  // hover 상태: 마우스를 올린 별의 인덱스 (0이면 호버 없음)
  // 사용자가 마우스를 별 위에 올리면 미리보기를 보여줍니다.
  const [hoverValue, setHoverValue] = useState(0);

  // --------------------------------------------------------
  // 별을 클릭했을 때
  // --------------------------------------------------------
  const handleClick = (starIndex) => {
    // readOnly가 아니고 onChange가 있을 때만 동작
    if (!readOnly && onChange) {
      onChange(starIndex);
    }
  };

  // --------------------------------------------------------
  // 마우스를 별 위에 올렸을 때
  // --------------------------------------------------------
  const handleMouseEnter = (starIndex) => {
    if (!readOnly) {
      setHoverValue(starIndex);
    }
  };

  // --------------------------------------------------------
  // 마우스가 별 영역을 떠났을 때
  // --------------------------------------------------------
  const handleMouseLeave = () => {
    if (!readOnly) {
      setHoverValue(0);
    }
  };

  return (
    <div
      className={`star-rating star-rating-${size} ${readOnly ? 'star-rating-readonly' : ''}`}
      onMouseLeave={handleMouseLeave}
    >
      {/* Array(5)로 5개의 별을 생성합니다 */}
      {/* [...Array(5)] → [undefined, undefined, undefined, undefined, undefined] */}
      {/* .map((_, index) → 각 요소에 대해 반복. index는 0, 1, 2, 3, 4 */}
      {[...Array(5)].map((_, index) => {
        // starIndex: 1~5 (배열 인덱스 0~4에 +1)
        const starIndex = index + 1;
        // 현재 보여줄 값: 호버 중이면 hoverValue, 아니면 실제 value
        const displayValue = hoverValue || value;
        // 이 별이 채워져야 하는지 판단
        const isFilled = starIndex <= displayValue;

        return (
          <span
            key={starIndex}
            className={`star ${isFilled ? 'star-filled' : 'star-empty'}`}
            onClick={() => handleClick(starIndex)}
            onMouseEnter={() => handleMouseEnter(starIndex)}
            // role과 aria-label: 접근성을 위한 속성
            role={readOnly ? undefined : 'button'}
            aria-label={`${starIndex}점`}
          >
            ★
          </span>
        );
      })}
    </div>
  );
}
