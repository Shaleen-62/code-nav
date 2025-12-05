# To run from root

python -m code_navigator.cli index ./test_repo

output:
[index] Repo: ./test_repo
[index] Codebase id: 0ee08a0953c25169
[index] Parsed graph in 0.02s
[index] Saved graph in 0.00s
[index] Nodes: 13, Edges: 14


python -m code_navigator.cli stats ./test_repo

[stats] Repo: ./test_repo
[stats] Codebase id: 0ee08a0953c25169
[stats] Nodes:     13
[stats] Edges:     14
[stats] Files:     3
[stats] Functions: 6
[stats] Classes:   4