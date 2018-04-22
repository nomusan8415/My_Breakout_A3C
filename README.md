# My_Breakout_A3C

【概要】 

・PyGameを使った自作ブロック崩しを、OpenAI Gym環境で、ChainerRlのA3Cアルゴリズムで走らせる。 

・Ubuntu上の最終バージョンのコピー

【現状】 

PyGameがマルチスレッドに対応していないため、PROCESSES>2では異常終了する。PROCESSES=1では正常に走るが、A#Cとして意味をなさない。

【今後の予定】 

・とりあえず、PyGameがマルチスレッド対応になるのを待つ。 

・マルチスレッドに対応した環境下で動くように改修する・
