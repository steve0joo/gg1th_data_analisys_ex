# 데이터 분석 및 시각화

## remote repository clone 및 git pull
- github에서 repository 만들기(README.md, .gitignore 추가)
- local 컴퓨터에서 clone하기
```
git clone your_git_url data_analisys_ex
```

## uv 가상환경 만들기
```
uv init --bare --python 3.12 --name data_analisys
```

## 라이브러리 설치
```
uv add numpy pandas
uv add lxml
uv add matplotlib
uv add seaborn
uv add xlrd
uv add plotly
```

## ipykernel에 가상환경 추가하기
- ipykernel 설치
```
uv add ipykernel
```

- 가상환경 추가
```
uv run python -m ipykernel install --user --name .venv --display-name "eda_env"
```