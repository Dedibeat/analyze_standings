#include<bits/stdc++.h>
using namespace std;
#define int long long
#define ff first
#define ss second
#define all(v) (v).begin(), (v).end()
#define hha(x) cout << #x << ": " << x << " "
#define hhal(x) cout << #x << ": " << x << endl
#define print(v) cout << #v << ": "; for(auto x : v) cout << x << " "; cout << endl;
void solve()
{
    int n, d; cin >> n >> d;
    multiset<int, greater<>> st;
    vector<int> a(n);
    for(auto &x : a) cin >> x;
    for(auto x : a)
    {
        auto it = st.lower_bound(x - d);
        if(it != st.begin())
        {
            st.erase(prev(it));
            st.insert(x);
            print(st);
            continue;
        }
        it = st.lower_bound(x - 2 * d);
        if(it != st.end())
        {
            st.erase(it);
            st.insert(x);
            print(st);
            continue;
        }
        st.insert(x);
        print(st);
    }
    cout << st.size() << '\n';
}
signed main()
{
    ios::sync_with_stdio(0); cin.tie(NULL);
    int t; cin >> t; while(t--)
    solve();
}
