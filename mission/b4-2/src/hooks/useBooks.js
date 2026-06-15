/**
 * ============================================================
 * useBooks.js — 독서 기록 목록 관리 커스텀 훅
 * ============================================================
 * 
 * [미션 요구사항 4.4 — 커스텀 훅 분리]
 *   "데이터 조회/갱신 흐름 중 최소 1개 이상은 커스텀 훅으로 분리되어야 한다"
 * 
 * 커스텀 훅(Custom Hook)이란?
 *   → 여러 컴포넌트에서 반복되는 로직(상태 + 효과)을 하나의 함수로 추출한 것.
 *   → 이름이 반드시 'use'로 시작해야 합니다 (React 규칙).
 *   → 컴포넌트가 아니라 "로직"을 재사용하는 것이 핵심입니다.
 * 
 * 이 훅이 관리하는 것:
 *   - books: 독서 기록 목록 배열
 *   - loading: 데이터 로딩 중인지
 *   - error: 에러 메시지
 *   - fetchBooks: 목록을 다시 불러오는 함수 (재시도 용도)
 *   - deleteBook: 특정 기록을 삭제하는 함수
 */

import { useState, useEffect, useCallback } from 'react';
import { supabase } from '../lib/supabase';

export default function useBooks() {
  // ============================================================
  // 상태 정의
  // ============================================================
  const [books, setBooks] = useState([]);     // 독서 기록 목록
  const [loading, setLoading] = useState(true); // 로딩 상태
  const [error, setError] = useState(null);    // 에러 메시지

  // ============================================================
  // fetchBooks — Supabase에서 독서 기록 목록을 가져오는 함수
  // ============================================================
  // useCallback으로 감싸는 이유:
  //   → 이 함수를 의존성 배열에 넣거나 자식에게 전달할 때,
  //     매 렌더링마다 새로운 함수가 생성되는 것을 방지합니다.
  //   → 이것이 보너스 5.2의 useCallback 적용입니다.
  const fetchBooks = useCallback(async () => {
    try {
      setLoading(true);  // 로딩 시작
      setError(null);     // 이전 에러 초기화

      // --------------------------------------------------------
      // Supabase 쿼리: books 테이블에서 데이터 조회
      // --------------------------------------------------------
      // .from('books') → books 테이블을 선택
      // .select('*')   → 모든 컬럼을 가져옴 (* = 전부)
      // .order('created_at', { ascending: false }) → 최신 순 정렬
      const { data, error: fetchError } = await supabase
        .from('books')
        .select('*')
        .order('created_at', { ascending: false });

      // Supabase에서 에러가 발생하면 throw
      if (fetchError) throw fetchError;

      // 성공 시 books 상태를 업데이트
      // data가 null일 수 있으므로 빈 배열로 대체
      setBooks(data || []);
    } catch (err) {
      // 에러 발생 시 error 상태에 메시지 저장
      setError(err.message || '데이터를 불러오는데 실패했습니다.');
    } finally {
      // try든 catch든 실행 후 항상 로딩을 false로
      setLoading(false);
    }
  }, []); // ← 빈 의존성: 이 함수의 로직은 바뀌지 않으므로 한 번만 생성

  // ============================================================
  // deleteBook — 특정 독서 기록을 삭제하는 함수
  // ============================================================
  const deleteBook = useCallback(async (id) => {
    try {
      // .from('books').delete() → 삭제 쿼리
      // .eq('id', id) → id가 일치하는 행만 삭제
      const { error: deleteError } = await supabase
        .from('books')
        .delete()
        .eq('id', id);

      if (deleteError) throw deleteError;

      // 삭제 성공 시, books 배열에서 해당 항목을 필터링하여 제거합니다.
      // .filter(): 조건을 만족하는 요소만 남기는 배열 메서드
      // book.id !== id → 삭제된 id가 아닌 항목만 남김
      setBooks(prev => prev.filter(book => book.id !== id));
      
      return true; // 성공
    } catch (err) {
      setError(err.message || '삭제에 실패했습니다.');
      return false; // 실패
    }
  }, []);

  // ============================================================
  // useEffect: 컴포넌트 마운트 시 자동으로 데이터 불러오기
  // ============================================================
  // 이 훅을 사용하는 컴포넌트가 화면에 나타나면 자동으로 fetchBooks를 실행합니다.
  useEffect(() => {
    fetchBooks();
  }, [fetchBooks]);

  // ============================================================
  // 반환값: 이 훅을 사용하는 컴포넌트에서 접근할 수 있는 값들
  // ============================================================
  return {
    books,       // 독서 기록 목록 배열
    loading,     // 로딩 중 여부
    error,       // 에러 메시지 (null이면 에러 없음)
    fetchBooks,  // 목록 새로고침 함수 (재시도 버튼에 사용)
    deleteBook,  // 삭제 함수
  };
}
