"""Ruby3.2.2 Random MT19937 initialization and required draw operations.

Port of Ruby v3_2_2 random.c and missing/mt19937.c; source hashes/locators
are in sources/schedule-generator-reference-lock.json. Upstream copyright
and BSD notices: package reference notice-ruby-random and sources/licenses/ruby-random.txt.
No Python random.Random substitution: Ruby's small-seed and leading-guard
initialization and bounded-integer rejection consume different source words.
"""
from .errors import GeneratorError

_MASK=0xffffffff
_ALGORITHM='ruby-3.2.2-mt19937-v1'

def _integer(value):
    return isinstance(value,int) and not isinstance(value,bool)

class SourceRandom:
    def __init__(self,seed: int):
        if not _integer(seed) or seed < 0:
            raise GeneratorError('invalid_seed','/seed','Source seed must be a nonnegative integer; no derived-seed width cap')
        self._seed=seed
        words=[];remaining=seed
        while remaining:
            words.append(remaining&_MASK);remaining >>= 32
        if len(words)<=1:
            self._initialize(seed)
        else:
            # Ruby removes the leading word 1 guard, but still uses init_by_array.
            if words[-1]==1:words.pop()
            self._initialize(19650218)
            i=1;j=0
            for _ in range(max(624,len(words))):
                previous=self._state[i-1]
                self._state[i]=((self._state[i]^((previous^(previous>>30))*1664525))+words[j]+j)&_MASK
                i+=1;j+=1
                if i==624:self._state[0]=self._state[623];i=1
                if j==len(words):j=0
            for _ in range(623):
                previous=self._state[i-1]
                self._state[i]=((self._state[i]^((previous^(previous>>30))*1566083941))-i)&_MASK
                i+=1
                if i==624:self._state[0]=self._state[623];i=1
            self._state[0]=0x80000000
        self._index=624

    def _initialize(self,seed):
        self._state=[seed&_MASK]
        for i in range(1,624):
            previous=self._state[-1]
            self._state.append((1812433253*(previous^(previous>>30))+i)&_MASK)

    def _word(self):
        if self._index==624:
            for i in range(624):
                mixed=(self._state[i]&0x80000000)|(self._state[(i+1)%624]&0x7fffffff)
                self._state[i]=self._state[(i+397)%624]^(mixed>>1)^(0x9908b0df if mixed&1 else 0)
            self._index=0
        value=self._state[self._index];self._index+=1
        value ^= value>>11
        value ^= (value<<7)&0x9d2c5680
        value ^= (value<<15)&0xefc60000
        value ^= value>>18
        return value

    def random(self) -> float:
        a=self._word()>>5;b=self._word()>>6
        return (a*67108864.0+b)/9007199254740992.0

    def randbelow(self,limit: int) -> int:
        if not _integer(limit) or limit<=0:
            raise GeneratorError('invalid_random_limit','/limit','Positive integer required')
        maximum=limit-1
        if maximum==0:return 0
        count=(maximum.bit_length()+31)//32
        top_mask=(1<<(((maximum.bit_length()-1)%32)+1))-1
        while True:
            value=0;boundary=True
            for position in range(count-1,-1,-1):
                word=self._word() & (top_mask if position==count-1 else _MASK)
                bound=(maximum>>(32*position))&_MASK
                if boundary:
                    if word>bound:break # Ruby retries immediately without drawing lower words.
                    if word<bound:boundary=False
                value=(value<<32)|word
            else:return value

    def getstate(self) -> dict:
        return {'algorithm':_ALGORITHM,'seed':self._seed,'state':list(self._state),'index':self._index}

    def setstate(self,state: dict) -> None:
        if (not isinstance(state,dict) or set(state)!={'algorithm','seed','state','index'}
            or state['algorithm']!=_ALGORITHM or not _integer(state['seed']) or state['seed']<0
            or not _integer(state['index']) or not 0<=state['index']<=624
            or not isinstance(state['state'],list) or len(state['state'])!=624
            or any(not _integer(w) or not 0<=w<=_MASK for w in state['state']) or not any(state['state'])):
            raise GeneratorError('invalid_random_state','/state','Invalid versioned Ruby MT19937 state')
        self._seed=state['seed'];self._index=state['index'];self._state=list(state['state'])
