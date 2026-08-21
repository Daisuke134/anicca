## ja
# AIに毎朝「仕事して」はもう古い？自走する仕組みのつくり方
AIエージェントを放置で動かすには、長いプロンプトより、起動・作業・検証・修復・停止をつなぐ反復構造が要る。これがLoop Engineeringだ。人が毎回指示し、終わりを判定する席まで、観測可能な完了条件と別の検証役へ置き換える。
## en
# Better Prompts Won’t Make Your AI Agent Run Every Day
An AI agent does not become autonomous because its prompt is longer. It becomes autonomous when the surrounding system knows when to wake it, what state to load, how to verify its work, how to recover from failure, and when to stop. That system is loop engineering: the design of recurring, observable workflows that replace a human who would otherwise keep prompting, checking, and restarting the agent. A useful loop begins with a measurable done condition, gives the work to a maker, sends the result to a fresh checker, and repeats only when the evidence says it should. Scheduling is only the alarm clock. The real engineering is the control system that lets an agent improve and repair its work without inventing success or running forever.
