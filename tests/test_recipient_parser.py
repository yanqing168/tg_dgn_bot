"""
测试收件人解析器
"""
import pytest
from src.premium.recipient_parser import RecipientParser


class TestRecipientParser:
    """测试收件人解析器"""
    
    def test_parse_single_username(self):
        """测试解析单个用户名"""
        text = "@alice"
        result = RecipientParser.parse(text)
        assert result == ["alice"]
    
    def test_parse_multiple_usernames(self):
        """测试解析多个用户名"""
        text = "@alice @bobby @charlie"
        result = RecipientParser.parse(text)
        assert set(result) == {"alice", "bobby", "charlie"}
    
    def test_parse_tme_links(self):
        """测试解析 t.me 链接"""
        text = "t.me/alice t.me/bobby"
        result = RecipientParser.parse(text)
        assert set(result) == {"alice", "bobby"}
    
    def test_parse_mixed_formats(self):
        """测试混合格式"""
        text = "@alice t.me/bobby @charlie"
        result = RecipientParser.parse(text)
        assert set(result) == {"alice", "bobby", "charlie"}
    
    def test_deduplicate_usernames(self):
        """测试去重"""
        text = "@alice @alice t.me/alice"
        result = RecipientParser.parse(text)
        assert result == ["alice"]
    
    def test_case_insensitive(self):
        """测试大小写不敏感"""
        text = "@Alice @ALICE @alice"
        result = RecipientParser.parse(text)
        assert result == ["alice"]
    
    def test_multiline_input(self):
        """测试多行输入"""
        text = """
        @alice
        @bobby
        t.me/charlie
        """
        result = RecipientParser.parse(text)
        assert set(result) == {"alice", "bobby", "charlie"}
    
    def test_validate_username(self):
        """测试用户名验证"""
        assert RecipientParser.validate_username("alice") is True
        assert RecipientParser.validate_username("alice_123") is True
        assert RecipientParser.validate_username("alice123") is True
        
        # 无效：太短
        assert RecipientParser.validate_username("abc") is False
        
        # 无效：包含特殊字符
        assert RecipientParser.validate_username("alice-bob") is False
        assert RecipientParser.validate_username("alice.bob") is False
        
        # 无效：太长
        assert RecipientParser.validate_username("a" * 33) is False
    
    def test_normalize_username(self):
        """测试用户名规范化"""
        assert RecipientParser.normalize("@Alice") == "alice"
        assert RecipientParser.normalize("Alice") == "alice"
        assert RecipientParser.normalize("  @Alice  ") == "alice"
    
    def test_parse_empty_text(self):
        """测试空文本"""
        text = ""
        result = RecipientParser.parse(text)
        assert result == []
    
    def test_parse_no_usernames(self):
        """测试无用户名文本"""
        text = "hello world 123"
        result = RecipientParser.parse(text)
        assert result == []
    
    def test_parse_with_punctuation(self):
        """测试包含标点符号"""
        text = "Recipients: @alice, @bobby, and @charlie!"
        result = RecipientParser.parse(text)
        assert set(result) == {"alice", "bobby", "charlie"}
