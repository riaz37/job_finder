"""
Unit tests for database service and connection management
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.db.database import DatabaseService, db_service, get_database, get_db_transaction


class TestDatabaseService:
    """Test cases for DatabaseService class"""
    
    @pytest.fixture
    def db_service_instance(self):
        """Create a fresh DatabaseService instance for testing"""
        return DatabaseService()
    
    @pytest.mark.asyncio
    async def test_connect_success(self, db_service_instance):
        """Test successful database connection"""
        with patch('app.db.database.Prisma') as mock_prisma:
            mock_db = AsyncMock()
            mock_prisma.return_value = mock_db
            
            await db_service_instance.connect()
            
            assert db_service_instance._connected is True
            assert db_service_instance.db is not None
            mock_db.connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_failure(self, db_service_instance):
        """Test database connection failure"""
        with patch('app.db.database.Prisma') as mock_prisma:
            mock_db = AsyncMock()
            mock_db.connect.side_effect = Exception("Connection failed")
            mock_prisma.return_value = mock_db
            
            with pytest.raises(Exception, match="Connection failed"):
                await db_service_instance.connect()
            
            assert db_service_instance._connected is False
    
    @pytest.mark.asyncio
    async def test_disconnect_success(self, db_service_instance):
        """Test successful database disconnection"""
        # First connect
        with patch('app.db.database.Prisma') as mock_prisma:
            mock_db = AsyncMock()
            mock_prisma.return_value = mock_db
            await db_service_instance.connect()
            
            # Then disconnect
            await db_service_instance.disconnect()
            
            assert db_service_instance._connected is False
            assert db_service_instance.db is None
            mock_db.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ensure_connected_when_not_connected(self, db_service_instance):
        """Test ensure_connected when not connected"""
        with patch('app.db.database.Prisma') as mock_prisma:
            mock_db = AsyncMock()
            mock_prisma.return_value = mock_db
            
            await db_service_instance.ensure_connected()
            
            assert db_service_instance._connected is True
            mock_db.connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ensure_connected_when_already_connected(self, db_service_instance):
        """Test ensure_connected when already connected"""
        with patch('app.db.database.Prisma') as mock_prisma:
            mock_db = AsyncMock()
            mock_prisma.return_value = mock_db
            
            # First connection
            await db_service_instance.connect()
            mock_db.connect.reset_mock()
            
            # Second call should not connect again
            await db_service_instance.ensure_connected()
            
            mock_db.connect.assert_not_called()
    
    def test_get_client_when_connected(self, db_service_instance):
        """Test get_client when database is connected"""
        mock_db = MagicMock()
        db_service_instance.db = mock_db
        
        client = db_service_instance.get_client()
        
        assert client is mock_db
    
    def test_get_client_when_not_connected(self, db_service_instance):
        """Test get_client when database is not connected"""
        with pytest.raises(RuntimeError, match="Database not connected"):
            db_service_instance.get_client()
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, db_service_instance):
        """Test successful health check"""
        with patch('app.db.database.Prisma') as mock_prisma:
            mock_db = AsyncMock()
            mock_db.user.count.return_value = 0
            mock_prisma.return_value = mock_db
            
            result = await db_service_instance.health_check()
            
            assert result is True
            mock_db.user.count.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, db_service_instance):
        """Test health check failure"""
        with patch('app.db.database.Prisma') as mock_prisma:
            mock_db = AsyncMock()
            mock_db.user.count.side_effect = Exception("Database error")
            mock_prisma.return_value = mock_db
            
            result = await db_service_instance.health_check()
            
            assert result is False


class TestDatabaseDependencies:
    """Test cases for database dependency functions"""
    
    @pytest.mark.asyncio
    async def test_get_database(self):
        """Test get_database dependency function"""
        with patch.object(db_service, 'ensure_connected') as mock_ensure:
            with patch.object(db_service, 'get_client') as mock_get_client:
                mock_client = MagicMock()
                mock_get_client.return_value = mock_client
                
                result = await get_database()
                
                mock_ensure.assert_called_once()
                mock_get_client.assert_called_once()
                assert result is mock_client
    
    @pytest.mark.asyncio
    async def test_get_db_transaction_success(self):
        """Test successful database transaction context manager"""
        with patch.object(db_service, 'ensure_connected'):
            with patch.object(db_service, 'get_client') as mock_get_client:
                mock_db = AsyncMock()
                mock_transaction = AsyncMock()
                
                # Create a proper async context manager mock
                mock_context_manager = AsyncMock()
                mock_context_manager.__aenter__.return_value = mock_transaction
                mock_context_manager.__aexit__.return_value = None
                mock_db.tx.return_value = mock_context_manager
                
                mock_get_client.return_value = mock_db
                
                async with get_db_transaction() as tx:
                    assert tx is mock_transaction
                
                mock_db.tx.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_db_transaction_failure(self):
        """Test database transaction context manager with exception"""
        with patch.object(db_service, 'ensure_connected'):
            with patch.object(db_service, 'get_client') as mock_get_client:
                mock_db = AsyncMock()
                mock_transaction = AsyncMock()
                
                # Create a proper async context manager mock
                mock_context_manager = AsyncMock()
                mock_context_manager.__aenter__.return_value = mock_transaction
                mock_context_manager.__aexit__.return_value = None
                mock_db.tx.return_value = mock_context_manager
                
                mock_get_client.return_value = mock_db
                
                with pytest.raises(ValueError):
                    async with get_db_transaction() as tx:
                        raise ValueError("Transaction error")