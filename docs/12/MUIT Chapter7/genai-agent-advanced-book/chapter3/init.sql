-- テストデータベースの初期化スクリプト
-- このスクリプトはDocker Composeで自動的に実行されます

-- テストテーブルの作成
CREATE TABLE IF NOT EXISTS employees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(50),
    salary INTEGER,
    hire_date DATE
);

-- テストデータの挿入
INSERT INTO employees (name, department, salary, hire_date) VALUES
('Tanaka Taro', 'IT', 600000, '2020-04-01'),
('Yamada Hanako', 'HR', 550000, '2019-03-15'),
('Suzuki Ichiro', 'Finance', 700000, '2021-01-20'),
('Watanabe Yuki', 'IT', 650000, '2020-07-10'),
('Kato Akira', 'Marketing', 580000, '2022-02-01'),
('Nakamura Yui', 'IT', 620000, '2021-05-15'),
('Yoshida Saki', 'Finance', 680000, '2020-12-01'),
('Matsumoto Ryu', 'HR', 540000, '2022-08-20'),
('Inoue Kana', 'Marketing', 590000, '2021-11-10'),
('Takahashi Ken', 'IT', 710000, '2019-09-05');

-- データの確認
SELECT 'データベースの初期化が完了しました。従業員数:' as message, COUNT(*) as count FROM employees;
