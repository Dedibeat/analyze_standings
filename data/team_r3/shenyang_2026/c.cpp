#include<bits/stdc++.h>
using namespace std;
#define int long long
#define ff first
#define ss second
#define all(v) (v).begin(), (v).end()
#define hha(x) cout << #x << ": " << x << " "
#define hhal(x) cout << #x << ": " << x << endl
#define print(v) cout << #v << ": "; for(auto x : v) cout << x << " "; cout << endl;
const int inf = 1e18;
struct Table
{
    int m, add;
    vector<vector<int>> v;
    vector<int> rmin;
    Table(int m) : m(m), add(0), v(m + 1, vector<int>(m + 1, inf)), rmin(m + 1, -1)
    {
        v[0][0] = 0;
        buildrow(0);
    }
    void lift(int A)
    {
        add += A;
    }
    int get(int i, int j)
    {
        return v[i][j] + add;
    }
    void upd(int i, int j, int val)
    {
        v[i][j] = min(v[i][j], val - add);
    }
    void buildrow(int i)
    {
        int mn = inf, mnj = -1;
        for(int j = 0; j <= m; j++)
        {
            if(mn > v[i][j]) mn = v[i][j], mnj = j;
        }
        rmin[i] = mnj;
    }
    pair<int, int> getmn(int i)
    {
        if(rmin[i] == -1) return {inf, -1};
        return {get(i, rmin[i]), rmin[i]};
    }
    void see()
    {
        for(int i = 0; i <= m; i++)
        for(int j = 0; j <= m; j++)
        {
            cout << get(i, j) << " \n"[j == m];
        }
    }
};
void solve()
{
    int n, m, A, B, C; cin >> n >> m >> A >> B >> C;
    Table tab(m);
    vector<array<int, 3>> patch;
    for(int it = 0; it < n; it++)
    {
        patch.clear();
        int x; cin >> x;
        for(int j = 0; j <= m; j++)
        {
            int cost = min(tab.get(x, j), tab.get(j, x)) + B;
            patch.push_back({x, j, cost});
        }
        for(int i = 0; i <= m; i++)
        {
            auto [cost, j] = tab.getmn(i);
            if(j == -1) continue;
            cost += C;
            patch.push_back({x, i, cost});
        }
        tab.lift(A);
        //cout << "patch:\n";
        for(auto &[i, j, cost] : patch)
        {
            //cout << i << " " << j << " " << cost << endl;
            tab.upd(i, j, cost);
        }
        //cout << "end\n";

        tab.buildrow(x);
        //tab.see();
    }

    int ans = inf;
    for(int i = 0; i <= m; i++)
    for(int j = 0; j <= m; j++)
    {
        ans = min(ans, tab.get(i, j));
    }
    cout << ans << "\n";
}
signed main()
{
    ios::sync_with_stdio(0); cin.tie(NULL);
    int t; cin >> t; while(t--)
    solve();
}
