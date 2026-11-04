"""직접 정의한 영어 불용어 목록.

세 묶음으로 나눈다. 각 묶음을 넣은 근거는 README '전처리 설계'에 적었다.
1. FUNCTION_WORDS: 관사·대명사·전치사·접속사·조동사 등 기능어. 어느 주제에나 고르게 나온다.
2. CONTRACTIONS: 아포스트로피를 지운 축약형(dont, im, ...). 정제 규칙 때문에 생기는 형태다.
3. NEWSGROUP_WORDS: 게시판 글쓰기 관습에서 나오는 말(writes, article, ...)과
   주제와 무관하게 빈도가 높은 일반 동사·부사. 범주를 가르는 단어(game, image, space)는 넣지 않는다.
"""

FUNCTION_WORDS = """
a about above across after again against all almost alone along already also although always am
among an and another any anybody anyone anything anyway anywhere are around as at be became because
become becomes been before behind being below beside besides between beyond both but by can cannot
could did do does doing done down during each either else elsewhere enough etc even ever every
everyone everything everywhere few for from further had has have having he her here hers herself him
himself his how however i if in indeed into is it its itself just least less many may me meanwhile
might mine more moreover most mostly much must my myself neither never nevertheless next no nobody
none nor not nothing now nowhere of off often on once one only onto or other others otherwise our ours
ourselves out over own per perhaps rather same several shall she should since so some somehow someone
something sometime sometimes somewhere still such than that the their theirs them themselves then
there thereafter thereby therefore these they this those though through throughout thus to together
too toward towards under until up upon us very via was we well were what whatever when whenever where
whereas wherever whether which while who whoever whole whom whose why will with within without would
yet you your yours yourself yourselves
"""

CONTRACTIONS = """
arent cant couldnt didnt doesnt dont hadnt hasnt havent hed hell hes id ill im ive isnt itd itll
lets mightnt mustnt shant shed shell shes shouldnt thats theres theyd theyll theyre theyve wasnt wed
well were weve werent whats wheres whos wont wouldnt youd youll youre youve
"""

NEWSGROUP_WORDS = """
article articles wrote writes writing said says say re subject post posted posting reply replies
thanks thank please hi hello regards anyone anybody somebody
get gets got getting go goes going gone make makes made making take takes took use used uses using
know knows knew think thinks thought want wants like likes seem seems seemed see seen look looks
really actually probably maybe sure quite pretty lot lots thing things way ways good better best bad
new old many much little first last also yes ok okay
"""

# 세 문자열을 공백으로 나누어 한 집합으로 합친다. 중첩 for는 묶음마다 단어를 순회한다.
# frozenset은 변경할 수 없는 집합이다. 중복 단어는 하나로 합쳐지고 tok in STOPWORDS로
# 포함 여부를 빠르게 확인한다. 목록 순서에는 의미가 없다.
# 예상: dont와 not가 모두 사라지면 부정 표현을 구별할까? 답: 구별하지 못한다.
STOPWORDS = frozenset(
    word for group in (FUNCTION_WORDS, CONTRACTIONS, NEWSGROUP_WORDS) for word in group.split()
)
