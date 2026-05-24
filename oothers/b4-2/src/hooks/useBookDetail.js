/**
 * ============================================================
 * useBookDetail.js — 독서 기록 상세 조회 커스텀 훅
 * ============================================================
 * 
 * 특정 독서 기록 1건의 상세 정보를 Supabase에서 가져옵니다.
 * 라우트 파라미터(URL의 :id 부분)에서 ID를 받아 해당 기록을 조회합니다.
 * 
 * 예: /books/abc-123 → useBookDetail('abc-123') → 해당 기록 조회
 */

import { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';

export default function useBookDetail(id) {
  // ============================================================
  // 상태 정의
  // ============================================================
  const [book, setBook] = useState(null);       // 독서 기록 데이터 (1건)
  const [loading, setLoading] = useState(true); // 로딩 상태
  const [error, setError] = useState(null);     // 에러 메시지

  // ============================================================
  // useEffect: id가 바뀔 때마다 해당 기록을 조회
  // ============================================================
  // 의존성 배열 [id] → id 값이 바뀔 때마다 다시 실행됩니다.
  // 즉, 사용자가 다른 기록의 상세 페이지로 이동하면 자동으로 새 데이터를 조회합니다.
  useEffect(() => {
    // id가 없으면(undefined/null) 조회하지 않음
    if (!id) return;

    const fetchBook = async () => {
      try {
        setLoading(true);
        setError(null);

        // --------------------------------------------------------
        // Supabase 쿼리: 특정 ID의 기록 1건 조회
        // --------------------------------------------------------
        // .eq('id', id) → id 컬럼이 파라미터 id와 같은 행만 선택
        // .single()     → 결과가 정확히 1건일 때 사용.
        //                  배열 대신 단일 객체를 반환합니다.
        const { data, error: fetchError } = await supabase
          .from('books')
          .select('*')
          .eq('id', id)
          .single();

        if (fetchError) throw fetchError;

        setBook(data);
      } catch (err) {
        setError(err.message || '데이터를 불러오는데 실패했습니다.');
      } finally {
        setLoading(false);
      }
    };

    fetchBook();
  }, [id]); // ← id가 바뀔 때만 재실행

  // ============================================================
  // 반환값
  // ============================================================
  return {
    book,     // 독서 기록 데이터 (객체 1건)
    loading,  // 로딩 중 여부
    error,    // 에러 메시지
  };
}
