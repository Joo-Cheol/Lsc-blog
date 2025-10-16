"""
네이버 블로그 HTML 렌더러
- 네이버 친화 HTML 출력
- 반응형 디자인 지원
- SEO 최적화
"""
import re
from typing import Dict, Any


class NaverHTMLRenderer:
    """네이버 블로그 HTML 렌더러"""
    
    def __init__(self):
        self.naver_styles = """
        <style>
        .blog-content {
            font-family: 'Malgun Gothic', sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .hook {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            font-size: 1.1em;
            font-weight: bold;
        }
        
        .case-example {
            background: #f8f9fa;
            border-left: 4px solid #007bff;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
        }
        
        .case-example h4 {
            color: #007bff;
            margin-top: 0;
        }
        
        .case-example p {
            margin: 8px 0;
        }
        
        .case-example strong {
            color: #495057;
        }
        
        .cta {
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            margin: 30px 0;
            font-size: 1.1em;
            font-weight: bold;
        }
        
        .hashtags {
            background: #e9ecef;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            text-align: center;
        }
        
        .hashtags a {
            color: #007bff;
            text-decoration: none;
            margin: 0 5px;
        }
        
        .hashtags a:hover {
            text-decoration: underline;
        }
        
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }
        
        h3 {
            color: #34495e;
            margin-top: 30px;
            margin-bottom: 15px;
            padding-left: 10px;
            border-left: 4px solid #3498db;
        }
        
        ol, ul {
            padding-left: 20px;
        }
        
        li {
            margin: 8px 0;
        }
        
        .checklist li {
            color: #27ae60;
            font-weight: 500;
        }
        
        .cautions li {
            color: #e74c3c;
            font-weight: 500;
        }
        
        .sources li {
            color: #7f8c8d;
            font-style: italic;
        }
        
        @media (max-width: 768px) {
            .blog-content {
                padding: 15px;
            }
            
            .hook, .cta {
                padding: 15px;
                font-size: 1em;
            }
        }
        </style>
        """
    
    def render_naver_html(self, topic: str, slots: Dict[str, str]) -> str:
        """
        네이버 친화 HTML 렌더링
        
        Args:
            topic: 주제
            slots: 채워진 슬롯들
            
        Returns:
            네이버 HTML
        """
        # 제목 생성
        title = self._generate_title(topic)
        
        # HTML 템플릿 적용
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <meta name="description" content="{topic}에 대한 전문적인 법적 가이드와 실무 절차를 상세히 안내합니다.">
            <meta name="keywords" content="{topic}, 채권추심, 법무법인, 법률상담">
            {self.naver_styles}
        </head>
        <body>
            <div class="blog-content">
                <h1>{title}</h1>
                
                <div class="hook">
                    {slots.get('hook', '')}
                </div>
                
                <h3>📋 실제 사례</h3>
                {slots.get('cases', '')}
                
                <h3>⚖️ 핵심 절차</h3>
                {slots.get('procedure', '')}
                
                <h3>✅ 체크리스트</h3>
                <div class="checklist">
                    {slots.get('checklist', '')}
                </div>
                
                <h3>⚠️ 주의사항</h3>
                <div class="cautions">
                    {slots.get('cautions', '')}
                </div>
                
                <div class="cta">
                    {slots.get('cta', '')}
                </div>
                
                <h3>📚 참고 자료</h3>
                <div class="sources">
                    {slots.get('sources', '')}
                </div>
                
                <div class="hashtags">
                    {slots.get('hashtags', '')}
                </div>
            </div>
        </body>
        </html>
        """
        
        return self._clean_html(html_content)
    
    def _generate_title(self, topic: str) -> str:
        """SEO 최적화 제목 생성"""
        # 제목 패턴들
        title_patterns = [
            f"{topic}, {self._get_random_period()} 안에 끝내는 핵심 절차 | 실무형 가이드",
            f"{topic} 완벽 가이드 | 전문가가 알려주는 실무 노하우",
            f"{topic} 절차와 주의사항 | 법무법인 전문가 조언",
            f"{topic} 성공 전략 | 단계별 실무 가이드"
        ]
        
        import random
        return random.choice(title_patterns)
    
    def _get_random_period(self) -> str:
        """랜덤 기간 생성"""
        import random
        periods = ["2주", "1개월", "6주", "2개월", "3개월"]
        return random.choice(periods)
    
    def _clean_html(self, html: str) -> str:
        """HTML 정리"""
        # 불필요한 공백 제거
        html = re.sub(r'\n\s*\n', '\n', html)
        html = re.sub(r'[ \t]+', ' ', html)
        
        # 빈 태그 정리
        html = re.sub(r'<(\w+)[^>]*>\s*</\1>', '', html)
        
        return html.strip()
    
    def render_markdown_to_html(self, markdown: str) -> str:
        """Markdown을 네이버 HTML로 변환"""
        # 기본 Markdown 변환
        html = markdown
        
        # 헤딩 변환
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        
        # 리스트 변환
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'^(\d+)\. (.+)$', r'<li>\2</li>', html, flags=re.MULTILINE)
        
        # 강조 변환
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        
        # 링크 변환
        html = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', html)
        
        return html
    
    def add_naver_meta_tags(self, html: str, topic: str) -> str:
        """네이버 최적화 메타 태그 추가"""
        meta_tags = f"""
        <meta property="og:title" content="{topic} 전문 가이드">
        <meta property="og:description" content="{topic}에 대한 법적 절차와 실무 노하우를 상세히 안내합니다.">
        <meta property="og:type" content="article">
        <meta property="og:site_name" content="법무법인 블로그">
        
        <meta name="twitter:card" content="summary_large_image">
        <meta name="twitter:title" content="{topic} 전문 가이드">
        <meta name="twitter:description" content="{topic}에 대한 법적 절차와 실무 노하우를 상세히 안내합니다.">
        
        <meta name="robots" content="index, follow">
        <meta name="author" content="법무법인 전문가">
        """
        
        # head 태그 안에 메타 태그 추가
        html = html.replace('</head>', f'{meta_tags}\n</head>')
        
        return html