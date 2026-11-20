#include<bits/stdc++.h>
using namespace std;
#define int long long
#define ff first
#define ss second
#define all(v) (v).begin(), (v).end()
#define hha(x) cout << #x << ": " << x << " "
#define hhal(x) cout << #x << ": " << x << endl
#define print(v) cout << #v << ": "; for(auto x : v) cout << x << " "; cout << endl;
struct AndTree
{
    int op(int a, int b) { return a & b; }
    int n, id = -1;
    vector<int> t;
    AndTree(int n) : n(n), t(2 * n + 5, id) {}
    void upd(int p, int x)
    {
        for(t[p += n] = x; p >>= 1; ) t[p] = op(t[2 * p], t[2 * p + 1]);
    }
    int get(int l, int r)
    {
        int res = id;
        for(l += n, r += n; l < r; l >>= 1, r >>= 1)
        {
            if(l & 1) res = op(res, t[l++]);
            if(r & 1) res = op(res, t[--r]);
        }
        return res;
    }
};
struct OrTree
{
    int op(int a, int b) { return a | b; }
    int n, id = 0;
    vector<int> t;
    OrTree(int n) : n(n), t(2 * n + 5, id) {}
    void upd(int p, int x)
    {
        //hha(p); hhal(x);
        for(t[p += n] = x; p >>= 1; ) t[p] = op(t[2 * p], t[2 * p + 1]);
    }
    int get(int l, int r)
    {
        int res = id;
        for(l += n, r += n; l < r; l >>= 1, r >>= 1)
        {
            if(l & 1) res = op(res, t[l++]);
            if(r & 1) res = op(res, t[--r]);
        }
        return res;
    }
};
struct SumTree
{
    int op(int a, int b) { return a + b; }
    int n, id = 0;
    vector<int> t;
    SumTree(int n) : n(n), t(2 * n + 5, id) {}
    void add(int p, int x)
    {
        if(p < 0) return;
        for(t[p += n] += x; p >>= 1; ) t[p] = op(t[2 * p], t[2 * p + 1]);
    }
    int get(int l, int r)
    {
        int res = id;
        for(l += n, r += n; l < r; l >>= 1, r >>= 1)
        {
            if(l & 1) res = op(res, t[l++]);
            if(r & 1) res = op(res, t[--r]);
        }
        return res;
    }
};
void solve()
{
    int n, m, q; cin >> n >> m >> q;
    vector<pair<int, int>> v;
    vector<int> a(n);
    for(int i = 0; i < n; i++)
    {
        cin >> a[i];
        v.push_back({a[i], i});
    }
    vector<array<int, 2>> b(n), c(n);
    for(int i = 0; i < n; i++) b[i] = {i, i}, c[i] = {i, i};
    sort(all(v));
    OrTree ort(n);
    for(auto [x, i] : v)
    {
        int l = i, r = i;
        for(int d = (1 << 20); d > 0; d >>= 1)
        {
            {
                int nl = max(0LL, l - d);
                int val = ort.get(nl, i);
                if(x == 6)
                {
                    //hha(nl); hha(i); hhal(val);
                }
                if(val == (val & x))
                {
                    l = nl;
                }
            }
            {
                int nr = min(n - 1, r + d);
                int val = ort.get(i + 1, nr + 1);
                if(val == (val & x))
                {
                    r = nr;
                }
            }
        }
        b[i] = {l, r};
        //hha(i); hha(l); hhal(r);
        ort.upd(i, x);
    }
    //cout << endl;
    sort(all(v), greater<>());
    AndTree andt(n);
    for(auto [x, i] : v)
    {
        int l = i, r = i;
        for(int d = (1 << 20); d > 0; d >>= 1)
        {
            {
                int nl = max(0LL, l - d);
                int val = andt.get(nl, i);
                if(x == (val & x))
                {
                    l = nl;
                }
            }
            {
                int nr = min(n - 1, r + d);
                int val = andt.get(i + 1, nr + 1);
                if(x == (val & x))
                {
                    r = nr;
                }
            }
        }
        //hha(i); hha(l); hhal(r);
        c[i] = {l, r};
        andt.upd(i, x);
    }
    vector<int> ans(q);
    vector<vector<pair<int, int>>> patch(n);
    for(int id = 0; id < q; id++)
    {
        int l, r; cin >> l >> r;
        l--, r--;
        patch[l].push_back({r, id});
    }
    vector<vector<array<int, 2>>> add(n), rem(n);
    for(int i = 0; i < n; i++)
    {
        int l = max(b[i][0], c[i][0]);
        int r = min(b[i][1], c[i][1]);
        //hha(l); hhal(r);
        add[l].push_back({r, i});
        rem[i].push_back({r, i});
    }
    //cout << endl;
    SumTree sumt(n);
    for(int i = 0; i < n; i++)
    {
        for(auto [r, j] : add[i])
        {
            //hha(i); hhal(r);
            sumt.add(r, 1);
            sumt.add(j - 1, -1);
        }
        for(auto [r, idx] : patch[i])
        {
            ans[idx] = sumt.get(r, n);
        }
        for(auto [r, j] : rem[i])
        {
            sumt.add(r, -1);
            sumt.add(j - 1, 1);
        }
    }
    //print(ans);
    for(auto x : ans) cout << x << "\n";

}
signed main()
{
    ios::sync_with_stdio(0); cin.tie(NULL);
    //int t; cin >> t; while(t--)
    solve();
}
