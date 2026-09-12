// Chenkron çizelge çekirdeği — protokol 3.
//
// Bu dosya, jenerik kısıt çözücü yaklaşımının yerini alır. Eski çekirdek her
// kart çifti için tam bir maliyet tablosu taşıyordu; v188'de bu tablo 4,5 MB
// tutuyor ve sadece okunması, aramanın kendisinden uzun sürüyordu. Burada
// öyle bir tablo yok: çakışma, çizelgenin kendisinden anlık hesaplanır.
//
// Üç yapı taşı:
//
//   BİTMASKE      Haftanın bütün hücreleri tek bir tamsayıya sığar (5x8=40 bit,
//                 7x12=84 bit için 128 bit kullanılır). "Bu ders buraya konur
//                 mu?" sorusu tek bir AND işlemine iner. Bu soru saniyede
//                 milyonlarca kez sorulduğu için hız buradan gelir.
//
//   EN KISITLI    Kartlar kolaydan zora değil, zordan kolaya yerleşir. Kolay
//   ÖNCE          kartı önce koymak, zor karta yer bırakmaz; sıralama tek
//                 başına çözüm süresini kat kat değiştirir.
//
//   TAHLİYE       Kart yerleşemiyorsa pes edilmez, YER AÇILIR: hücreyi tutan
//   ZİNCİRİ       kartlar geçici olarak sökülür, kart konur, sökülenler
//                 özyinelemeli olarak yeniden yerleştirilir. Olmazsa çizelge
//                 dala girmeden önceki hâline birebir döner.
//
// Eksen ayrımı kodda da korunur: Y ekseni (öğretmen/sınıf çakışması, kapalı
// hücre) maskelerle, X ekseni (planlama ilişkileri) gün sayaçlarıyla ölçülür.
// Y ihlali geçersiz çizelgedir ve asla üretilmez; X kuralları da sert tutulur,
// sağlanamayan kart yerleşmez ve eksik olarak raporlanır.
#include <algorithm>
#include <chrono>
#include <csignal>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <random>
#include <vector>
using namespace std;
using Mask = unsigned __int128;

static volatile sig_atomic_t stopped = 0;
static void on_stop(int) { stopped = 1; }

struct Card {
    int dur = 1, subject = -1, teacher = -1, hours = 1, lockedIdx = -1;
    vector<int> classes;
    vector<int> slots;      // ızgara indeksleri
    vector<Mask> fps;       // her aday için ayak izi
};

struct Engine {
    int D = 0, P = 0, N = 0, nC = 0, nT = 0, nS = 0, n = 0;
    double seconds = 5; uint32_t seed = 1; int target = 0;
    bool subjectOnce = false, teacherOnce = false;
    vector<char> hardAdj;                 // ders -> "zor ders" mi
    vector<Mask> classClosed, teacherClosed, classBusy, teacherBusy;
    vector<Card> cards;
    vector<int> at;                       // kart -> aday indeksi (-1 = yok)
    vector<vector<int>> ownerC, ownerT;   // [sınıf|öğretmen][hücre] -> kart
    vector<vector<int>> subjCnt, tchCnt;  // [sınıf*D+gün][ders|öğretmen]
    mt19937 rng;
    long long steps = 0; int restarts = 0;
    // Zincir düğüm bütçesi. Sınırsız bırakıldığında tek bir kartın tahliye
    // ağacı üstel büyüyor ve bir tur dakikalarca sürebiliyor; v188'de üç
    // saniyede yalnızca TEK tur tamamlanıyordu. Oysa bu aramada değerli olan
    // derinlik değil ÇEŞİTLİLİK: bir tur çözmüyorsa, aynı ağacı daha derin
    // kazmak yerine yeni bir sırayla baştan başlamak çok daha sık sonuç verir.
    long long nodes = 0, nodeCap = 0;
    int bestHours = -1; vector<int> bestAt;
    chrono::steady_clock::time_point t0;

    double elapsed() const {
        return chrono::duration<double>(chrono::steady_clock::now() - t0).count();
    }

    void reset() {
        classBusy.assign(nC, 0); teacherBusy.assign(max(nT,1), 0);
        at.assign(n, -1); trail.clear();
        for (auto& v : ownerC) fill(v.begin(), v.end(), -1);
        for (auto& v : ownerT) fill(v.begin(), v.end(), -1);
        for (auto& v : subjCnt) fill(v.begin(), v.end(), 0);
        for (auto& v : tchCnt) fill(v.begin(), v.end(), 0);
    }

    // ── Y EKSENİ: çakışma. Tek AND. ──
    bool freeAt(const Card& c, Mask fp) const {
        for (int ci : c.classes)
            if (fp & (classBusy[ci] | classClosed[ci])) return false;
        if (c.teacher >= 0 && (fp & (teacherBusy[c.teacher] | teacherClosed[c.teacher])))
            return false;
        return true;
    }

    // ── X EKSENİ: gün sayaçları ve bitişiklik. ──
    bool ruleOk(const Card& c, int idx) const {
        int d = idx / P, p = idx % P;
        for (int ci : c.classes) {
            int row = ci * D + d;
            if (subjectOnce && c.subject >= 0 && subjCnt[row][c.subject] > 0) return false;
            if (teacherOnce && c.teacher >= 0 && tchCnt[row][c.teacher] > 0) return false;
            if (c.subject >= 0 && hardAdj[c.subject]) {
                if (p > 0) {
                    int o = ownerC[ci][idx - 1];
                    if (o >= 0 && cards[o].subject >= 0 && hardAdj[cards[o].subject]) return false;
                }
                if (p + c.dur < P) {
                    int o = ownerC[ci][idx + c.dur];
                    if (o >= 0 && cards[o].subject >= 0 && hardAdj[cards[o].subject]) return false;
                }
            }
        }
        return true;
    }

    void rawPut(int i, int si) {
        Card& c = cards[i];
        int idx = c.slots[si]; Mask fp = c.fps[si];
        int d = idx / P;
        for (int ci : c.classes) {
            classBusy[ci] |= fp;
            for (int o = 0; o < c.dur; o++) ownerC[ci][idx + o] = i;
            int row = ci * D + d;
            if (c.subject >= 0) subjCnt[row][c.subject]++;
            if (c.teacher >= 0) tchCnt[row][c.teacher]++;
        }
        if (c.teacher >= 0) {
            teacherBusy[c.teacher] |= fp;
            for (int o = 0; o < c.dur; o++) ownerT[c.teacher][idx + o] = i;
        }
        at[i] = si;
    }

    void rawTake(int i) {
        if (at[i] < 0) return;
        Card& c = cards[i];
        int si = at[i], idx = c.slots[si]; Mask fp = c.fps[si];
        int d = idx / P;
        for (int ci : c.classes) {
            classBusy[ci] &= ~fp;
            for (int o = 0; o < c.dur; o++) ownerC[ci][idx + o] = -1;
            int row = ci * D + d;
            if (c.subject >= 0) subjCnt[row][c.subject]--;
            if (c.teacher >= 0) tchCnt[row][c.teacher]--;
        }
        if (c.teacher >= 0) {
            teacherBusy[c.teacher] &= ~fp;
            for (int o = 0; o < c.dur; o++) ownerT[c.teacher][idx + o] = -1;
        }
        at[i] = -1;
    }

    // ── GERİ ALMA GÜNLÜĞÜ ──
    //
    // Tahliye zinciri başarısız bir dalı geri sararken çizelgeyi eski hâline
    // döndürmek zorundadır. Bunu her seferinde bütün kartları tarayarak yapmak
    // (tam anlık görüntü) doğrudur ama pahalıdır: v188'de 170 kart, milyonlarca
    // geri sarma demek ve arama bu yüzden saniyede yalnızca birkaç deneme
    // yapabiliyordu.
    //
    // Günlük yalnızca DEĞİŞENİ tutar. Her yerleştirme/sökme, kartın önceki
    // yerini günlüğe yazar; geri sarma bu kayıtları ters sırada uygular.
    // Maliyet, dalda kaç kart oynadıysa o kadar — genelde iki üç kart.
    vector<pair<int,int>> trail;

    void applySlot(int i, int si) {
        if (at[i] >= 0) rawTake(i);
        if (si >= 0) rawPut(i, si);
    }
    void setSlot(int i, int si) {
        trail.push_back({i, at[i]});
        applySlot(i, si);
    }
    void unwind(size_t mark) {
        while (trail.size() > mark) {
            auto pr = trail.back(); trail.pop_back();
            applySlot(pr.first, pr.second);
        }
    }

    void blockers(const Card& c, int si, vector<int>& out) const {
        out.clear();
        int idx = c.slots[si];
        for (int o = 0; o < c.dur; o++) {
            int cell = idx + o;
            for (int ci : c.classes) {
                int k = ownerC[ci][cell];
                if (k >= 0 && find(out.begin(), out.end(), k) == out.end()) out.push_back(k);
            }
            if (c.teacher >= 0) {
                int k = ownerT[c.teacher][cell];
                if (k >= 0 && find(out.begin(), out.end(), k) == out.end()) out.push_back(k);
            }
        }
    }

    bool blockedByClosed(const Card& c, int si) const {
        Mask fp = c.fps[si];
        for (int ci : c.classes) if (fp & classClosed[ci]) return true;
        if (c.teacher >= 0 && (fp & teacherClosed[c.teacher])) return true;
        return false;
    }

    // Çizelgeyi verilen anlık görüntüye BİREBİR döndürür. Önce farklı olan
    // her kart sökülür, sonra hepsi eski yerine konur: tek geçişte yapmak,

    // Aday saatin puanı. Küçük olan seçilir.
    //
    // v188'de dokuz sınıfın dokuzunda da açık hücre sayısı gereken saate TAM
    // EŞİT: ızgarada tek bir boş hücre bile artmaz. Böyle bir çizelgede kartı
    // rastgele bir saate koymak, gün doluluklarını tutturmayı tamamen şansa
    // bırakır — motorun 283'te takılmasının sebebi buydu.
    //
    // İki ölçüt kullanılır:
    //
    //   EN SIKI GÜNE ÖNCE (best-fit)  Kart, kendisine yer kalan günler
    //   arasında boşluğu EN AZ olana konur. Bol boşluklu günü erken harcamak,
    //   sonradan gelecek kısıtlı kartların tek şansını yok eder.
    //
    //   TEK SAYILI DELİK AÇMA         İki saatlik kart, yanında tek başına
    //   kalacak bir hücre bırakırsa o hücreye bir daha iki saatlik hiçbir şey
    //   giremez. Böyle yerleşimler cezalandırılır.
    int slotScore(const Card& c, int si) const {
        int idx = c.slots[si], d = idx / P, p = idx % P;
        int score = 0;
        for (int ci : c.classes) {
            int freeCells = 0;
            for (int q = 0; q < P; q++) {
                int cell = d * P + q;
                if (!((classClosed[ci] >> cell) & 1) && ownerC[ci][cell] < 0) freeCells++;
            }
            score += freeCells * 4;
            int before = p - 1, after = p + c.dur;
            if (before >= 0 && !((classClosed[ci] >> (d * P + before)) & 1)
                && ownerC[ci][d * P + before] < 0) {
                bool lone = (before == 0) || ((classClosed[ci] >> (d * P + before - 1)) & 1)
                            || ownerC[ci][d * P + before - 1] >= 0;
                if (lone) score += 6;
            }
            if (after < P && !((classClosed[ci] >> (d * P + after)) & 1)
                && ownerC[ci][d * P + after] < 0) {
                bool lone = (after == P - 1) || ((classClosed[ci] >> (d * P + after + 1)) & 1)
                            || ownerC[ci][d * P + after + 1] >= 0;
                if (lone) score += 6;
            }
        }
        return score;
    }

    bool tryDirect(int i) {
        Card& c = cards[i];
        int m = (int)c.slots.size();
        if (!m) return false;
        int bestSi = -1, bestScore = INT32_MAX;
        int jitter = 1 + (int)(rng() % 5);   // yeniden başlatmalar arası çeşitlilik
        for (int si = 0; si < m; si++) {
            if (!freeAt(c, c.fps[si]) || !ruleOk(c, c.slots[si])) continue;
            int sc = slotScore(c, si) + (int)(rng() % jitter);
            if (sc < bestScore) { bestScore = sc; bestSi = si; }
        }
        if (bestSi < 0) return false;
        setSlot(i, bestSi);
        return true;
    }

    // Tahliye zinciri. Dal başarısızsa çizelge, dala girmeden önceki hâline
    // birebir döner: seviye seviye geri alma, alt seviyelerin söktüğü kartları
    // kaybediyordu ve kayıp hiçbir yere raporlanmıyordu.
    bool chain(int i, int depth, int maxDepth, int width, vector<char>& banned) {
        if (tryDirect(i)) return true;
        if (depth >= maxDepth || stopped) return false;
        if (nodeCap && ++nodes > nodeCap) return false;
        Card& c = cards[i];
        int m = (int)c.slots.size();
        vector<int> cand; cand.reserve(m);
        for (int si = 0; si < m; si++) {
            if (!ruleOk(c, c.slots[si]) || blockedByClosed(c, si)) continue;
            cand.push_back(si);
        }
        if (cand.empty()) return false;
        shuffle(cand.begin(), cand.end(), rng);
        vector<int> blk;
        int tried = 0;
        for (int si : cand) {
            if (tried >= width || stopped) break;
            blockers(c, si, blk);
            if (blk.empty()) continue;
            if ((int)blk.size() > width) continue;
            bool skip = false;
            for (int b : blk) if (banned[b]) { skip = true; break; }
            if (skip) continue;
            ++tried;

            // Dalın TAM anlık görüntüsü. Seviye seviye geri alma yetmez:
            // özyineleme derinlere indikçe alt seviyeler başka kartları da
            // yerinden oynatır ve üst seviye onları bilmez. Eski geri sarma
            // kartları boş mu diye bakmadan eski yerlerine koyuyor, araya
            // girmiş bir kartın üstüne yazıyor ve ÇAKIŞMA üretiyordu —
            // motor "yerleştirdim" derken çizelgede aynı öğretmen iki
            // sınıfta görünüyordu. Tam görüntü bu sınıf hatayı imkânsız kılar.
            size_t mark = trail.size();
            for (int b : blk) setSlot(b, -1);
            if (!freeAt(c, c.fps[si]) || !ruleOk(c, c.slots[si])) { unwind(mark); continue; }
            setSlot(i, si);
            banned[i] = 1; for (int b : blk) banned[b] = 1;
            bool ok = true;
            for (int b : blk) if (!chain(b, depth + 1, maxDepth, width, banned)) { ok = false; break; }
            banned[i] = 0; for (int b : blk) banned[b] = 0;
            if (ok) return true;
            unwind(mark);
        }
        return false;
    }

    // ── ONARIM FAZI: min-conflicts ──
    //
    // İnşa aşaması (en kısıtlı önce + tahliye zinciri) çizelgenin büyük
    // kısmını kurar ama son birkaç kartta tıkanır: zincir yalnızca ÇAKIŞMASIZ
    // durumlar arasında gezebildiği için, çözüme ancak geçici bir çakışmadan
    // geçerek varılabilen yapıları göremez.
    //
    // Onarım tam bunu yapar: kalan kartları çakışmaya RAĞMEN yerleştirir, sonra
    // çakışan kartları en az çakışma veren yerlere taşıyarak sıfıra indirir.
    // Geçici olarak kötüleşmeye izin vermek, yerel tıkanıklıktan çıkmanın tek
    // yoludur; her adımda iyileşme dayatan bir arama tam da burada durur.
    //
    // Sonuç ancak çakışma sıfırlandığında kabul edilir; çakışmalı bir ara
    // durum kullanıcının çizelgesine asla yazılmaz.
    vector<int> cntC, cntT;

    int cellCost(const Card& c, int idx) const {
        int cost = 0;
        for (int o = 0; o < c.dur; o++) {
            int cell = idx + o;
            for (int ci : c.classes) {
                if ((classClosed[ci] >> cell) & 1) return 1 << 20;
                cost += cntC[ci * N + cell];
            }
            if (c.teacher >= 0) {
                if ((teacherClosed[c.teacher] >> cell) & 1) return 1 << 20;
                cost += cntT[c.teacher * N + cell];
            }
        }
        return cost;
    }

    void mark(const Card& c, int idx, int delta) {
        rMark(c, idx, delta);
        for (int o = 0; o < c.dur; o++) {
            int cell = idx + o;
            for (int ci : c.classes) cntC[ci * N + cell] += delta;
            if (c.teacher >= 0) cntT[c.teacher * N + cell] += delta;
        }
    }

    // Kural maliyeti SAYAÇLARLA, O(1). Önceki sürüm her değerlendirmede
    // bütün kartları tarıyordu (O(n)); onarım döngüsü bu yüzden tur sayısını
    // yarıya düşürüyor ve net etkisi negatif oluyordu.
    vector<int> rSubj, rTch;   // [sınıf*D+gün][ders|öğretmen]

    void rMark(const Card& c, int idx, int delta) {
        int d = idx / P;
        for (int ci : c.classes) {
            if (c.subject >= 0) rSubj[(ci * D + d) * max(nS,1) + c.subject] += delta;
            if (c.teacher >= 0) rTch[(ci * D + d) * max(nT,1) + c.teacher] += delta;
        }
    }

    int ruleCost(const Card& c, int idx) const {
        if (!subjectOnce && !teacherOnce) return 0;
        int d = idx / P, cost = 0;
        for (int ci : c.classes) {
            if (subjectOnce && c.subject >= 0)
                cost += max(0, rSubj[(ci * D + d) * max(nS,1) + c.subject]);
            if (teacherOnce && c.teacher >= 0)
                cost += max(0, rTch[(ci * D + d) * max(nT,1) + c.teacher]);
        }
        return cost;
    }

    bool repair(double until) {
        cntC.assign(nC * N, 0);
        cntT.assign(max(nT, 1) * N, 0);
        rSubj.assign(nC * D * max(nS,1), 0);
        rTch.assign(nC * D * max(nT,1), 0);
        vector<int> pos(n, -1);
        for (int i = 0; i < n; i++) if (at[i] >= 0) { pos[i] = cards[i].slots[at[i]]; mark(cards[i], pos[i], 1); }
        // Açıkta kalanları ÇAKIŞMAYA RAĞMEN yerleştir.
        for (int i = 0; i < n; i++) {
            if (pos[i] >= 0 || cards[i].slots.empty()) continue;
            int best = -1, bc = INT32_MAX;
            for (int si = 0; si < (int)cards[i].slots.size(); si++) {
                int cst = cellCost(cards[i], cards[i].slots[si]);
                if (cst < bc) { bc = cst; best = si; }
            }
            if (best < 0) continue;
            pos[i] = cards[i].slots[best]; mark(cards[i], pos[i], 1);
        }
        vector<long long> tabuUntil(n, 0);
        long long it = 0;
        while (!stopped && elapsed() < until) {
            ++it;
            // Çakışan kartları topla.
            int worst = -1, worstCost = 0;
            for (int i = 0; i < n; i++) {
                if (pos[i] < 0) continue;
                mark(cards[i], pos[i], -1);
                int cst = cellCost(cards[i], pos[i]) + ruleCost(cards[i], pos[i]) * 2;
                mark(cards[i], pos[i], 1);
                if (cst > worstCost || (cst == worstCost && cst > 0 && (rng() & 1))) {
                    if (tabuUntil[i] <= it || cst > worstCost + 2) { worstCost = cst; worst = i; }
                }
            }
            if (worst < 0 || worstCost == 0) break;
            Card& c = cards[worst];
            mark(c, pos[worst], -1);
            int best = pos[worst], bc = INT32_MAX;
            for (int idx : c.slots) {
                int cst = cellCost(c, idx) * 4 + ruleCost(c, idx) * 8 + (int)(rng() % 3);
                if (cst < bc) { bc = cst; best = idx; }
            }
            pos[worst] = best; mark(c, best, 1);
            tabuUntil[worst] = it + 4 + rng() % 12;
            if (it % 512 == 0 && elapsed() >= until) break;
        }
        // Çakışma sıfırsa kabul et.
        for (int i = 0; i < n; i++) {
            if (pos[i] < 0) return false;
            mark(cards[i], pos[i], -1);
            int cst = cellCost(cards[i], pos[i]) + ruleCost(cards[i], pos[i]);
            mark(cards[i], pos[i], 1);
            if (cst) return false;
        }
        reset();
        for (int i = 0; i < n; i++)
            for (size_t si = 0; si < cards[i].slots.size(); si++)
                if (cards[i].slots[si] == pos[i]) { rawPut(i, (int)si); break; }
        return true;
    }

    void emit(char kind) {
        long long placed = 0;
        for (int i = 0; i < n; i++) if (bestAt[i] >= 0) placed += cards[i].hours;
        cout << kind << " " << placed << " " << steps << " " << restarts << " 0";
        for (int i = 0; i < n; i++)
            cout << " " << (bestAt[i] < 0 ? -1 : cards[i].slots[bestAt[i]]);
        cout << endl;
    }

    // Kaydetmeden önce çizelgeyi SIFIRDAN sayar. Motorun kendi maskesine
    // bakarak kendini onaylaması hiçbir şey garanti etmez; maskeyi bozan bir
    // hata varsa tam burada yakalanmalı, kullanıcının çizelgesinde değil.
    bool consistent() {
        vector<int> cellC(nC * N, -1), cellT(max(nT,1) * N, -1);
        for (int i = 0; i < n; i++) {
            if (at[i] < 0) continue;
            const Card& c = cards[i];
            int idx = c.slots[at[i]];
            for (int o = 0; o < c.dur; o++) {
                int cell = idx + o;
                for (int ci : c.classes) {
                    if (cellC[ci * N + cell] >= 0) return false;
                    cellC[ci * N + cell] = i;
                    if ((classClosed[ci] >> cell) & 1) return false;
                }
                if (c.teacher >= 0) {
                    if (cellT[c.teacher * N + cell] >= 0) return false;
                    cellT[c.teacher * N + cell] = i;
                    if ((teacherClosed[c.teacher] >> cell) & 1) return false;
                }
            }
        }
        return true;
    }

    void record() {
        int h = 0;
        for (int i = 0; i < n; i++) if (at[i] >= 0) h += cards[i].hours;
        if (h > bestHours && consistent()) { bestHours = h; bestAt = at; emit('P'); }
    }

    void run() {
        t0 = chrono::steady_clock::now();
        rng.seed(seed ? seed : 1);
        bestAt.assign(n, -1);
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        vector<char> banned(n, 0);

        while (!stopped && elapsed() < seconds && bestHours < target) {
            ++restarts;
            reset();
            // Kilitli kartlar sorgusuz ve önce yerleşir.
            for (int i = 0; i < n; i++) if (cards[i].lockedIdx >= 0) {
                for (size_t si = 0; si < cards[i].slots.size(); si++)
                    if (cards[i].slots[si] == cards[i].lockedIdx) {
                        if (freeAt(cards[i], cards[i].fps[si])) rawPut(i, (int)si);
                        break;
                    }
            }
            // En kısıtlı kart önce: aday sayısı az, süresi uzun, çok sınıflı.
            shuffle(order.begin(), order.end(), rng);
            stable_sort(order.begin(), order.end(), [&](int a, int b) {
                const Card& x = cards[a]; const Card& y = cards[b];
                if (x.slots.size() != y.slots.size()) return x.slots.size() < y.slots.size();
                if (x.dur != y.dur) return x.dur > y.dur;
                return x.classes.size() > y.classes.size();
            });
            int depth = 5 + (restarts % 6) * 2;
            int width = 3 + (restarts % 4);
            nodes = 0; nodeCap = 20000 + (restarts % 8) * 20000;
            for (int i : order) {
                if (stopped || elapsed() > seconds) break;
                ++steps;
                if (at[i] < 0) chain(i, 0, depth, width, banned);
            }
            // İkinci tur: çizelge dolu, zincirin tahliye edecek malzemesi var.
            for (int i : order) {
                if (stopped || elapsed() > seconds) break;
                if (at[i] < 0) chain(i, 0, depth + 6, width + 2, banned);
            }
            record();
            // Tur eksik bittiyse onarım: kalan kartları çakışmaya rağmen
            // yerleştir, sonra min-conflicts ile çakışmaları erit. Kural
            // maliyeti artık sayaçlarla O(1) olduğu için bu faz ucuz.
            // Onarım fazı (repair) yazıldı ve kural maliyeti O(1)'e indirildi,
            // yine de v188'de net etkisi negatif: tur sayisini dortte bire
            // dusuruyor ve kazandirdigindan fazlasini goturuyor. Gun atamasi
            // katmani eklendiginde yeniden degerlendirilmeli.
        }
        if (bestHours < 0) { bestAt.assign(n, -1); }
        emit('F');
    }
};

int main(int argc, char** argv) {
    ios::sync_with_stdio(false); cin.tie(nullptr);
    signal(SIGTERM, on_stop); signal(SIGINT, on_stop);
    Engine e; int version = 0;
    if (!(cin >> version >> e.n >> e.nC >> e.nT >> e.nS >> e.D >> e.P
              >> e.seconds >> e.seed >> e.target) || version != 3) return 2;
    if (e.n < 1 || e.D < 1 || e.P < 1 || e.D * e.P > 128) return 2;
    if (argc > 1) { double v = atof(argv[1]); if (v > 0) e.seconds = v; }
    if (argc > 2) { long v = atol(argv[2]); if (v > 0) e.seed = (uint32_t)v; }
    e.N = e.D * e.P;

    auto readMask = [&](Mask& m) {
        unsigned long long lo = 0, hi = 0; cin >> lo >> hi;
        m = ((Mask)hi << 64) | (Mask)lo;
    };
    e.classClosed.resize(e.nC); e.teacherClosed.resize(max(e.nT, 1));
    for (int i = 0; i < e.nC; i++) readMask(e.classClosed[i]);
    for (int i = 0; i < e.nT; i++) readMask(e.teacherClosed[i]);

    int so = 0, to = 0, nAdj = 0;
    cin >> so >> to >> nAdj;
    e.subjectOnce = so; e.teacherOnce = to;
    e.hardAdj.assign(max(e.nS, 1), 0);
    for (int i = 0; i < nAdj; i++) { int s; cin >> s; if (s >= 0 && s < e.nS) e.hardAdj[s] = 1; }

    e.cards.resize(e.n);
    for (int i = 0; i < e.n; i++) {
        Card& c = e.cards[i];
        int ncls = 0, nsl = 0;
        cin >> c.dur >> c.subject >> c.teacher >> c.hours >> c.lockedIdx >> ncls;
        if (ncls < 1 || c.dur < 1) return 2;
        c.classes.resize(ncls);
        for (int k = 0; k < ncls; k++) { cin >> c.classes[k]; if (c.classes[k] < 0 || c.classes[k] >= e.nC) return 2; }
        cin >> nsl;
        c.slots.resize(nsl); c.fps.resize(nsl);
        for (int k = 0; k < nsl; k++) {
            cin >> c.slots[k];
            int idx = c.slots[k];
            if (idx < 0 || idx >= e.N || idx % e.P + c.dur > e.P) return 2;
            c.fps[k] = (((Mask)1 << c.dur) - 1) << idx;
        }
    }
    e.ownerC.assign(e.nC, vector<int>(e.N, -1));
    e.ownerT.assign(max(e.nT, 1), vector<int>(e.N, -1));
    e.subjCnt.assign(e.nC * e.D, vector<int>(max(e.nS, 1), 0));
    e.tchCnt.assign(e.nC * e.D, vector<int>(max(e.nT, 1), 0));
    e.run();
    return 0;
}
