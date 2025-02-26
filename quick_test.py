import requests

def test_cpp_judge():
    url = 'http://localhost:8000/judge'
    data = {
        "type": "cpp",
        "solution": """#include <cstdio>
#include <unistd.h>
int main(){sleep(3);printf("a");return 0;}
""",
        "expected_output": "a"
    }
    response = requests.post(url, json=data)
    print(response.json())
    assert response.status_code == 200
    assert response.json()['success']

    data = {
        "type": "cpp",
        "solution": """#include <cstdio>
int main(){printf("a");return 0;}
""",
        "expected_output": "b"
    }
    response = requests.post(url, json=data)
    print(response.json())
    assert response.status_code == 200
    assert not response.json()['success']


def test_python_judge():
    url = 'http://localhost:8000/judge'
    data = {
        "type": "python",
        "solution": "print(input())",
        "input": "a",
        "expected_output": "a"
    }
    response = requests.post(url, json=data)
    print(response.json())
    assert response.status_code == 200
    assert response.json()['success']

    data = {
        "type": "python",
        "solution": "print(input())",
        "input": "a",
        "expected_output": "b"
    }
    response = requests.post(url, json=data)
    print(response.json())
    assert response.status_code == 200
    assert not response.json()['success']


def test_batch_judge():
    url = 'http://localhost:8000/judge/batch'
    data = {
        'type': 'batch',
        "submissions": [{
        "type": "cpp",
        "solution": """#include <cstdio>
int main(){printf("a");return 0;}
""",
        "expected_output": "b"
        }, {
        "type": "python",
        "solution": "print(input())",
        "input": "a",
        "expected_output": "b"
        }, {
            "type": "python",
            "solution": "print(input())",
            "input": "a",
            "expected_output": "a"
        }, {
            "type": "cpp",
            "solution": """#include <cstdio>
#include <unistd.h>
int main(){sleep(3);printf("a");return 0;}
""",
            "expected_output": "a"
        }]
    }
    response = requests.post(url, json=data)
    print(response.json())
    assert response.status_code == 200
    results = response.json()['results']

    assert len(results) == 4
    assert not results[0]['success']
    assert not results[1]['success']
    assert results[2]['success']
    assert results[3]['success']


if __name__ == "__main__":
    test_cpp_judge()
    test_python_judge()
    test_batch_judge()
