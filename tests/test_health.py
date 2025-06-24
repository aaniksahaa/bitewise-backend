def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/api/v1/health/app-health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"} 