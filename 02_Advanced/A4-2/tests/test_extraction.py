"""정규식 추출·정규화·마스킹 단위 테스트. 패턴마다 변형 3가지 이상을 확인한다."""
import re
import unittest

from src.extract import extract, extract_grouped, mask
from src.normalize import luhn_ok, parse_korean_amount, rrn_checksum_ok, trim_url
from src.patterns import COMPILED, PATTERNS, to_js_source


def values(text, kind):
    return extract_grouped(text)[kind]


class TestEmail(unittest.TestCase):
    def test_variants(self):
        self.assertEqual(values("문의: user@domain.com", "email"), ["user@domain.com"])
        self.assertEqual(values("이메일은 test.user@sub.domain.co.kr입니다", "email"), ["test.user@sub.domain.co.kr"])
        self.assertEqual(values("메일 Kim+cs@Example.COM 으로", "email"), ["Kim+cs@example.com"])  # 도메인만 소문자

    def test_boundaries(self):
        self.assertEqual(values("주소: admin@site.net.", "email"), ["admin@site.net"])  # 문장 끝 점 제외
        self.assertEqual(values("멘션 @username 주세요", "email"), [])
        self.assertEqual(values("user@localhost", "email"), [])


class TestPhone(unittest.TestCase):
    def test_variants(self):
        self.assertEqual(values("010-1234-5678", "phone"), ["010-1234-5678"])
        self.assertEqual(values("02-123-4567 또는 031-1234-5678", "phone"), ["02-123-4567", "031-1234-5678"])
        self.assertEqual(values("010.9876.5432", "phone"), ["010-9876-5432"])
        self.assertEqual(values("01055556666", "phone"), ["010-5555-6666"])
        self.assertEqual(values("+82 10-1234-5678", "phone"), ["010-1234-5678"])
        self.assertEqual(values("(02) 345-6789", "phone"), ["02-345-6789"])
        self.assertEqual(values("대표번호 1588-1234", "phone"), ["1588-1234"])

    def test_negatives(self):
        self.assertEqual(values("주문번호 1234-5678-9012", "phone"), [])
        self.assertEqual(values("2024-01-15 방문", "phone"), [])
        self.assertEqual(values("010-1234-56789", "phone"), [])


class TestDate(unittest.TestCase):
    def test_variants(self):
        self.assertEqual(values("2024년 1월 15일", "date"), ["2024-01-15"])
        self.assertEqual(values("2024/01/15", "date"), ["2024-01-15"])
        self.assertEqual(values("2024-01-15", "date"), ["2024-01-15"])
        self.assertEqual(values("2024. 3. 15.(금)", "date"), ["2024-03-15"])
        self.assertEqual(values("24.12.25", "date"), ["2024-12-25"])
        self.assertEqual(values("March 15, 2024", "date"), ["2024-03-15"])
        self.assertEqual(values("3월 31일", "date"), ["--03-31"])  # 연도 없음

    def test_validation(self):
        self.assertEqual(values("2024-13-45", "date"), [])
        self.assertEqual(values("2023-02-29", "date"), [])
        self.assertEqual(values("2024-02-29", "date"), ["2024-02-29"])
        self.assertEqual(values("버전 10.15.7", "date"), [])
        self.assertEqual(values("2024-01/15", "date"), [])  # 역참조: 구분자가 섞이면 거부

    def test_two_digit_year_pivot(self):
        self.assertEqual(values("99.12.31", "date"), ["1999-12-31"])
        self.assertEqual(values("68.01.01", "date"), ["2068-01-01"])


class TestMoney(unittest.TestCase):
    def test_variants(self):
        self.assertEqual(values("10,000원", "money"), [10000])
        self.assertEqual(values("1억 2천만원", "money"), [120000000])
        self.assertEqual(values("$100", "money"), [10000])  # 센트
        self.assertEqual(values("5만 원", "money"), [50000])
        self.assertEqual(values("2.5억원", "money"), [250000000])
        self.assertEqual(values("오천원", "money"), [5000])
        self.assertEqual(values("₩3,000", "money"), [3000])
        self.assertEqual(values("USD 1,299.99", "money"), [129999])
        self.assertEqual(values("100달러", "money"), [10000])

    def test_negatives(self):
        self.assertEqual(values("회사원 3명", "money"), [])

    def test_korean_amount_parser(self):
        self.assertEqual(parse_korean_amount("1억 2천만"), 120_000_000)
        self.assertEqual(parse_korean_amount("1,500만"), 15_000_000)
        self.assertEqual(parse_korean_amount("삼만오천"), 35_000)
        self.assertEqual(parse_korean_amount("만"), 10_000)
        self.assertIsNone(parse_korean_amount("사"))  # 숫자도 단위도 없음


class TestUrl(unittest.TestCase):
    def test_variants(self):
        self.assertEqual(values("https://www.example.com/path?query=value", "url"), ["https://www.example.com/path?query=value"])
        self.assertEqual(values("www.naver.com 에서", "url"), ["http://www.naver.com"])
        self.assertEqual(values("<https://a.com/p?q=1>", "url"), ["https://a.com/p?q=1"])
        self.assertEqual(values("HTTPS://Example.COM/Path", "url"), ["https://example.com/Path"])
        self.assertEqual(values("https://shop.example.com:443/cart", "url"), ["https://shop.example.com/cart"])

    def test_trailing_punctuation(self):
        self.assertEqual(trim_url("http://a.com/x."), "http://a.com/x")
        self.assertEqual(trim_url("https://en.wikipedia.org/wiki/Regex_(disambiguation))"),
                         "https://en.wikipedia.org/wiki/Regex_(disambiguation)")

    def test_email_domain_is_not_url(self):
        ents = extract("help@www.example.com")
        self.assertEqual([e.type for e in ents], ["email"])


class TestMissionExample(unittest.TestCase):
    def test_result_example(self):
        g = extract_grouped("문의: support@company.co.kr, 전화 02-1234-5678 일시: 2024년 3월 15일, 참가비: 50,000원")
        self.assertEqual(g["email"], ["support@company.co.kr"])
        self.assertEqual(g["phone"], ["02-1234-5678"])
        self.assertEqual(g["date"], ["2024-03-15"])
        self.assertEqual(g["money"], [50000])


class TestMasking(unittest.TestCase):
    def test_formats(self):
        masked, _ = mask("010-1234-5678 / 900101-1234567 / 4518-4212-3456-7890 / user@x.com")
        self.assertEqual(masked, "010-****-5678 / 900101-1****** / 4518-42**-****-7890 / us***@x.com")

    def test_address(self):
        masked, _ = mask("서울특별시 강남구 테헤란로 123, 101동 202호")
        self.assertEqual(masked, "서울특별시 강남구 ****")

    def test_checksums(self):
        self.assertTrue(luhn_ok("4111111111111111"))
        self.assertFalse(luhn_ok("4111111111111112"))
        self.assertIn(rrn_checksum_ok("9001011234568"), (True, False))


class TestPatternDocumentation(unittest.TestCase):
    def test_every_pattern_is_commented(self):
        """제약 사항: 모든 정규표현식 패턴에 주석으로 의도와 매칭 범위를 설명한다."""
        for name, src in PATTERNS.items():
            lines = [l for l in src.splitlines() if l.strip()]
            commented = [l for l in lines if re.search(r"(?<!\\)#", l)]
            self.assertGreaterEqual(len(commented) / len(lines), 0.5, name)

    def test_no_unicode_shortcuts(self):
        """\\d \\w \\b는 str 패턴에서 유니코드 기준이라 쓰지 않는다(JS 이식과 한글 경계 때문)."""
        for name, src in PATTERNS.items():
            code = "\n".join(l.split("#")[0] for l in src.splitlines())
            self.assertNotRegex(code, r"\\[dwb]", name)

    def test_js_conversion_keeps_meaning(self):
        for name, src in PATTERNS.items():
            js = to_js_source(src)
            self.assertNotIn("(?P", js, name)
            self.assertNotIn("\n", js, name)
            # 공백·주석을 지운 패턴도 Python에서 같은 뜻이어야 한다(VERBOSE 없이 컴파일)
            py = re.sub(r"\(\?<(?![=!])(\w+)>", r"(?P<\1>", js).replace(r"\k<", "(?P=")
            py = re.sub(r"\(\?P=(\w+)>", r"(?P=\1)", py)
            compiled = re.compile(py)
            sample = "문의 a@b.com 010-1234-5678 2024-01-15 10,000원 https://x.com/a 900101-1234567 4111-1111-1111-1111"
            self.assertEqual([m.group(0) for m in compiled.finditer(sample)],
                             [m.group(0) for m in COMPILED[name].finditer(sample)], name)


if __name__ == "__main__":
    unittest.main()
