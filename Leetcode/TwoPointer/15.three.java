class Solution {
    public List<List<Integer>> threeSum(int[] nums) {
        Arrays.sort(nums); // 先排序
        List<List<Integer>> res = new ArrayList<>();
        
        for (int i = 0; i < nums.length; i++) {
            // 跳过重复元素
            if (i > 0 && nums[i] == nums[i - 1]) continue;
            
            // 双指针，目标是找到 nums[l] + nums[r] = -nums[i]
            int l = i + 1, r = nums.length - 1;
            int target = -nums[i];
            
            while (l < r) {
                int sum = nums[l] + nums[r];
                if (sum == target) {
                    res.add(Arrays.asList(nums[i], nums[l], nums[r]));
                    l++;
                    r--;
                    // 跳过重复元素
                    while (l < r && nums[l] == nums[l - 1]) l++;
                    while (l < r && nums[r] == nums[r + 1]) r--;
                } else if (sum < target) {
                    l++;
                } else {
                    r--;
                }
            }
        }
        
        return res;
    }
}