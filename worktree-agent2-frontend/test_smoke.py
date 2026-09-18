"""
test_smoke.py — Streamlit AppTest 기반 스모크 테스트
앱이 에러 없이 뜨는지 확인한다.
실행: python -m pytest test_smoke.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pytest


class TestAppSmoke:
    """앱이 에러 없이 초기 상태를 렌더링하는지 확인"""

    def test_app_initializes_without_exception(self):
        """AppTest로 앱 초기 로딩 시 예외 없음 확인"""
        try:
            from streamlit.testing.v1 import AppTest
        except ImportError:
            pytest.skip("streamlit.testing.v1 사용 불가 (Streamlit 1.28+ 필요)")

        app_path = os.path.join(os.path.dirname(__file__), "app.py")
        at = AppTest.from_file(app_path, default_timeout=30)
        at.run()

        # 예외가 없어야 함
        assert not at.exception, f"앱 실행 중 예외 발생: {at.exception}"

    def test_app_has_upload_section(self):
        """업로드 섹션 마크다운이 렌더링되어야 함"""
        try:
            from streamlit.testing.v1 import AppTest
        except ImportError:
            pytest.skip("streamlit.testing.v1 사용 불가")

        app_path = os.path.join(os.path.dirname(__file__), "app.py")
        at = AppTest.from_file(app_path, default_timeout=30)
        at.run()

        assert not at.exception
        # 마크다운 요소 중 '업로드' 관련 텍스트가 있어야 함
        all_markdown = [m.value for m in at.markdown]
        has_upload = any("업로드" in md for md in all_markdown)
        assert has_upload, f"업로드 관련 마크다운 없음. 마크다운 목록: {all_markdown[:5]}"

    def test_app_has_analyze_button(self):
        """분석 시작 버튼이 렌더링되어야 함"""
        try:
            from streamlit.testing.v1 import AppTest
        except ImportError:
            pytest.skip("streamlit.testing.v1 사용 불가")

        app_path = os.path.join(os.path.dirname(__file__), "app.py")
        at = AppTest.from_file(app_path, default_timeout=30)
        at.run()

        assert not at.exception
        # 버튼 목록에 "분석 시작" 포함 여부 확인
        button_labels = [b.label for b in at.button]
        assert any("분석" in label for label in button_labels), \
            f"분석 버튼 없음. 버튼 목록: {button_labels}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
