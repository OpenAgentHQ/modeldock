from unittest.mock import Mock
from modeldock.core.registry import RegistryService
from modeldock.domain.model import ModelSpec

def test_search_backward_compatibility():
    mock_port = Mock()
    mock_port.search.return_value = [Mock(spec=ModelSpec)]
    service = RegistryService(registry=mock_port)
    
    results = service.search("llama")
    
    assert len(results) == 1
    mock_port.search.assert_called_once_with("llama")

def test_search_with_keyword_filters():
    mock_port = Mock()
    
    # Create fake model specs for filtering
    m1 = Mock(spec=ModelSpec, category="text", capabilities=["chat"], ram=8)
    m2 = Mock(spec=ModelSpec, category="image", capabilities=["vision"], ram=16)
    
    # When query is empty, it calls list_all
    mock_port.list_all.return_value = [m1, m2]
    service = RegistryService(registry=mock_port)
    
    # Test category filter
    assert len(service.search(category="image")) == 1
    assert service.search(category="image")[0] == m2
    
    # Test capability filter
    assert len(service.search(capability="chat")) == 1
    
    # Test min_ram filter
    assert len(service.search(min_ram=10)) == 1
    assert service.search(min_ram=10)[0] == m2