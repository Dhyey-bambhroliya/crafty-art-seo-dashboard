import pytest

def create_users_and_tokens(client):
    # Manager
    m_res = client.post("/api/auth/setup-manager", json={
        "email": "manager@craftyart.com",
        "full_name": "SEO Manager",
        "password": "Password123"
    }).json()
    mgr_token = m_res["access_token"]
    mgr_headers = {"Authorization": f"Bearer {mgr_token}"}

    # Leader 1
    l1_res = client.post("/api/users", headers=mgr_headers, json={
        "email": "leader1@craftyart.com",
        "full_name": "Priya Sharma",
        "password": "Password123",
        "role": "TEAM_LEADER"
    }).json()
    l1_id = l1_res["id"]
    l1_login = client.post("/api/auth/login", json={"email": "leader1@craftyart.com", "password": "Password123"}).json()
    l1_headers = {"Authorization": f"Bearer {l1_login['access_token']}"}

    # Leader 2
    l2_res = client.post("/api/users", headers=mgr_headers, json={
        "email": "leader2@craftyart.com",
        "full_name": "Rahul Verma",
        "password": "Password123",
        "role": "TEAM_LEADER"
    }).json()
    l2_id = l2_res["id"]
    l2_login = client.post("/api/auth/login", json={"email": "leader2@craftyart.com", "password": "Password123"}).json()
    l2_headers = {"Authorization": f"Bearer {l2_login['access_token']}"}

    return mgr_headers, (l1_id, l1_headers), (l2_id, l2_headers)

def test_category_ownership_isolation(client):
    mgr_headers, (l1_id, l1_headers), (l2_id, l2_headers) = create_users_and_tokens(client)

    # Leader 1 creates Category 1
    cat1_res = client.post("/api/categories", headers=l1_headers, json={
        "name": "Invitation Templates",
        "description": "Wedding & Birthday Invitations",
        "assigned_leader_id": l1_id
    })
    assert cat1_res.status_code == 200
    cat1_id = cat1_res.json()["id"]

    # Leader 2 attempts to edit Leader 1's Category (MUST FAIL with 403 Forbidden)
    l2_edit = client.put(f"/api/categories/{cat1_id}", headers=l2_headers, json={
        "name": "Hacked Category Name"
    })
    assert l2_edit.status_code == 403
    assert "Permission denied" in l2_edit.json()["detail"]

    # Leader 2 attempts to add page to Leader 1's Category (MUST FAIL with 403)
    l2_add_page = client.post(f"/api/categories/{cat1_id}/pages", headers=l2_headers, json={
        "full_url": "https://craftyartapp.com/unauthorized"
    })
    assert l2_add_page.status_code == 403

    # Manager CAN edit Leader 1's Category
    mgr_edit = client.put(f"/api/categories/{cat1_id}", headers=mgr_headers, json={
        "description": "Manager updated description"
    })
    assert mgr_edit.status_code == 200
    assert mgr_edit.json()["description"] == "Manager updated description"

def test_page_duplicate_and_cross_category_warnings(client):
    mgr_headers, (l1_id, l1_headers), (l2_id, l2_headers) = create_users_and_tokens(client)

    # Cat 1 by Leader 1
    c1 = client.post("/api/categories", headers=l1_headers, json={
        "name": "Cat 1",
        "assigned_leader_id": l1_id
    }).json()["id"]

    # Cat 2 by Leader 2
    c2 = client.post("/api/categories", headers=l2_headers, json={
        "name": "Cat 2",
        "assigned_leader_id": l2_id
    }).json()["id"]

    url = "https://craftyartapp.com/flyer-maker?utm_source=test"
    # Add page to Cat 1
    p1 = client.post(f"/api/categories/{c1}/pages", headers=l1_headers, json={"full_url": url})
    assert p1.status_code == 200
    assert p1.json()["normalized_url"] == "https://craftyartapp.com/flyer-maker"

    # Attempt adding duplicate to same category must fail (400)
    p1_dup = client.post(f"/api/categories/{c1}/pages", headers=l1_headers, json={"full_url": url})
    assert p1_dup.status_code == 400

    # Checking duplicate check endpoint in Cat 2 should give warning about Cat 1 mapping
    check_res = client.post(f"/api/categories/{c2}/pages/check-duplicate", headers=l2_headers, json={"full_url": url})
    assert check_res.status_code == 200
    data = check_res.json()
    assert data["is_duplicate_in_category"] is False
    assert data["is_mapped_to_other_categories"] is True
    assert "Cat 1" in data["other_category_names"]
    assert "double counting" in data["warning_message"]

def test_bulk_pages_duplicate_check_and_bulk_add(client):
    mgr_headers, (l1_id, l1_headers), (l2_id, l2_headers) = create_users_and_tokens(client)

    # Cat 1 created by Leader 1
    c1 = client.post("/api/categories", headers=l1_headers, json={
        "name": "Social Media Templates",
        "assigned_leader_id": l1_id
    }).json()["id"]

    # Cat 2 created by Leader 2
    c2 = client.post("/api/categories", headers=l2_headers, json={
        "name": "Marketing Assets",
        "assigned_leader_id": l2_id
    }).json()["id"]

    # First, add a page to Cat 2
    client.post(f"/api/categories/{c2}/pages", headers=l2_headers, json={
        "full_url": "https://craftyartapp.com/templates/instagram-story"
    })

    # Leader 1 checks a bulk list for Cat 1:
    # 1. Fresh URL 1: https://craftyartapp.com/templates/facebook-cover
    # 2. Fresh URL 2: https://craftyartapp.com/templates/youtube-thumbnail?utm_source=fb
    # 3. Cross-category URL: https://craftyartapp.com/templates/instagram-story
    # 4. Invalid URL: not-a-valid-url
    # 5. Duplicate within submission: https://craftyartapp.com/templates/facebook-cover?ref=share
    check_bulk = client.post(f"/api/categories/{c1}/pages/check-duplicates-bulk", headers=l1_headers, json={
        "urls": [
            "https://craftyartapp.com/templates/facebook-cover",
            "https://craftyartapp.com/templates/youtube-thumbnail?utm_source=fb",
            "https://craftyartapp.com/templates/instagram-story",
            "not-a-valid-url",
            "https://craftyartapp.com/templates/facebook-cover?ref=share"
        ]
    })
    assert check_bulk.status_code == 200
    check_data = check_bulk.json()
    assert len(check_data["items"]) == 5
    assert check_data["total_valid"] == 3  # facebook-cover, youtube-thumbnail, instagram-story
    assert check_data["total_warnings"] == 1  # instagram-story is in Cat 2
    assert check_data["total_duplicates"] == 1  # facebook-cover repeated

    # Now perform bulk add to Cat 1
    add_bulk = client.post(f"/api/categories/{c1}/pages/bulk", headers=l1_headers, json={
        "urls": [
            "https://craftyartapp.com/templates/facebook-cover",
            "https://craftyartapp.com/templates/youtube-thumbnail?utm_source=fb",
            "https://craftyartapp.com/templates/instagram-story",
            "not-a-valid-url",
            "https://craftyartapp.com/templates/facebook-cover?ref=share"
        ]
    })
    assert add_bulk.status_code == 200
    bulk_result = add_bulk.json()
    assert bulk_result["added_count"] == 3
    assert bulk_result["skipped_count"] == 2  # 1 invalid + 1 duplicate of facebook-cover
    assert len(bulk_result["warnings"]) == 1
    assert len(bulk_result["pages"]) == 3

    # Check that category now lists the 3 newly added pages
    cat1_pages = client.get(f"/api/categories/{c1}/pages", headers=l1_headers).json()
    assert len(cat1_pages) == 3
